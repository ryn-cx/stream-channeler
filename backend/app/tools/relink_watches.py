# TODO: Validate
"""Point detached watches back at an episode.

Deleting an episode leaves its watches behind with no `episode_id`. A watch
still names what it watched, so once an episode carrying that
copy of that episode exists again the watch can be attached to it. An episode
usually has a copy on several sources, so the one the `User` ranked highest is
chosen, exactly as playback would.
"""

from collections import defaultdict
from typing import TYPE_CHECKING
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col, select

from app.canonical_episodes.models import CanonicalEpisode
from app.database import engine, load_models
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from app.watches.models import Watch

if TYPE_CHECKING:
    from app.channels.episode_selector import SourceDedupConfig

# `episode_selector` aliases `Episode` as it is imported, which maps every model
# a mapped model names, so it is imported after the models are loaded rather
# than alongside them.
load_models()


# TODO: Validate
def _detached_watches(session: Session) -> list[Watch]:
    """Return every watch left without an episode."""
    return list(
        session.exec(select(Watch).where(col(Watch.episode_id).is_(None))).all(),
    )


# TODO: Validate
def _candidates_by_canonical_key(
    session: Session,
    canonical_keys: set[str],
) -> dict[str, list[tuple[Episode, str]]]:
    """Return the live copies of each watched key, with their source key."""
    if not canonical_keys:
        return {}

    rows = session.exec(
        select(CanonicalEpisode.key, Episode, Source.key)  # type: ignore[call-overload]
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(
            CanonicalEpisode,
            col(CanonicalEpisode.id) == col(Episode.canonical_episode_id),
        )
        .where(
            col(CanonicalEpisode.key).in_(canonical_keys),
            col(Episode.deleted_at).is_(None),
        ),
    ).all()

    candidates: dict[str, list[tuple[Episode, str]]] = defaultdict(list)
    for canonical_key, episode, source_key in rows:
        candidates[canonical_key].append((episode, source_key))
    return candidates


# TODO: Validate
def _preferred_episode(
    candidates: list[tuple[Episode, str]],
    config: SourceDedupConfig,
) -> Episode:
    """Return the candidate whose source the `User` ranked highest.

    Ties break on the episode id so a rerun makes the same choice, matching how
    playback collapses the copies of one episode.
    """
    episode, _ = min(
        candidates,
        key=lambda candidate: (config.priority_for(candidate[1]), str(candidate[0].id)),
    )
    return episode


# TODO: Validate
def _config_for_user(
    session: Session,
    user_id: UUID,
    cache: dict[UUID, SourceDedupConfig],
) -> SourceDedupConfig:
    """Return a `User`'s source priorities, resolved once per run."""
    from app.channels.episode_selector import source_dedup_config  # noqa: PLC0415

    if user_id not in cache:
        cache[user_id] = source_dedup_config(session, session.get(User, user_id))
    return cache[user_id]


# TODO: Validate
def _report_unresolvable(session: Session, canonical_keys: set[str]) -> None:
    """Log why the watches on `canonical_keys` have nothing to be pointed at.

    A watch outlives the episode it names, so it can name one this database has
    never held, and there is nothing a rerun will do about it until that episode
    is imported. Saying which of the two it is separates a library that has yet
    to catch up from an episode that was deleted and is still there to restore.
    """
    if not canonical_keys:
        return

    soft_deleted = set(
        session.exec(
            select(CanonicalEpisode.key)
            .join(
                Episode,
                col(Episode.canonical_episode_id) == col(CanonicalEpisode.id),
            )
            .where(col(CanonicalEpisode.key).in_(canonical_keys)),
        ).all(),
    )
    unknown = canonical_keys - soft_deleted
    logger.info(
        "{} episodes have only a deleted copy, {} have no copy at all",
        len(soft_deleted),
        len(unknown),
    )
    if unknown:
        logger.info(
            "Episodes with no copy, first few: {}",
            ", ".join(sorted(unknown)[:5]),
        )


# TODO: Validate
def relink_watches(session: Session) -> int:
    """Attach every detached watch that has an episode to point at again."""
    detached = _detached_watches(session)
    if not detached:
        logger.info("No detached watches to relink")
        return 0

    logger.info("Found {} detached watches", len(detached))
    canonical_keys = {watch.canonical_episode_key for watch in detached}
    candidates = _candidates_by_canonical_key(session, canonical_keys)
    _report_unresolvable(session, canonical_keys - candidates.keys())
    configs: dict[UUID, SourceDedupConfig] = {}

    relinked = 0
    for watch in detached:
        matches = candidates.get(watch.canonical_episode_key)
        if not matches:
            continue

        config = _config_for_user(session, watch.user_id, configs)
        episode = _preferred_episode(matches, config)
        watch.episode_id = episode.id
        relinked += 1
        logger.info(
            "Relinked watch {} to episode {} ({})",
            watch.id,
            episode.key,
            watch.canonical_episode_key,
        )

    session.commit()
    logger.info("Relinked {} of {} detached watches", relinked, len(detached))
    return relinked


if __name__ == "__main__":
    with Session(engine) as session:
        relink_watches(session)
