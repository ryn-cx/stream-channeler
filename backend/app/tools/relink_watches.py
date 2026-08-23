# TODO: Validate
"""Point detached watches back at an episode.

Deleting an episode leaves its watches behind with no `episode_id`. A watch still names
what it watched, so once an episode carrying that non-canonical row of that episode
exists again the watch can be attached to it. An episode usually has a non-canonical row
on several sources, so the one the `User` ranked highest is chosen, exactly as playback
would.
"""

from collections import defaultdict
from typing import TYPE_CHECKING, Any
from uuid import UUID

from loguru import logger
from sqlmodel import Session, col, select

from app.canonical_media.episodes import (
    canonical_episode_id_column,
    canonical_episode_link,
    links_of,
)
from app.canonical_media.filters import is_non_canonical
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
def _named_episodes(watch_identifiers: set[str]) -> Any:  # noqa: ANN401 - A subquery of the episodes the watches name.
    """Return each named episode paired with the episode it answers to."""
    named_link = canonical_episode_link()
    return (
        select(
            col(Episode.watch_identifier).label("watch_identifier"),
            canonical_episode_id_column(Episode, named_link).label(
                "canonical_episode_id",
            ),
        )
        .select_from(Episode)
        .outerjoin(named_link, links_of(Episode, named_link))
        .where(col(Episode.watch_identifier).in_(watch_identifiers))
        .subquery()
    )


# TODO: Validate
def _candidates_by_watch_identifier(
    session: Session,
    watch_identifiers: set[str],
) -> dict[str, list[tuple[Episode, str]]]:
    """Return the live links to each watched identifier, with their source key.

    An identifier is a link's own, so the rows it can be pointed at are the
    other links standing for the same episode - which is what the identifier is
    read back to first.
    """
    if not watch_identifiers:
        return {}

    canonical_link = canonical_episode_link()
    named = _named_episodes(watch_identifiers)
    rows = session.exec(
        select(named.c.watch_identifier, Episode, Source.key)  # type: ignore[call-overload]
        .select_from(Episode)
        .join(Season, col(Season.id) == col(Episode.season_id))
        .join(Show, col(Show.id) == col(Season.show_id))
        .join(Source, col(Source.id) == col(Show.source_id))
        .join(canonical_link, links_of(Episode, canonical_link))
        .join(
            named,
            named.c.canonical_episode_id == col(canonical_link.canonical_episode_id),
        )
        .where(
            is_non_canonical(Episode),
            col(Episode.deleted_at).is_(None),
        ),
    ).all()

    candidates: dict[str, list[tuple[Episode, str]]] = defaultdict(list)
    for watch_identifier, episode, source_key in rows:
        candidates[watch_identifier].append((episode, source_key))
    return candidates


# TODO: Validate
def _preferred_episode(
    candidates: list[tuple[Episode, str]],
    config: SourceDedupConfig,
) -> Episode:
    """Return the candidate whose source the `User` ranked highest.

    Ties break on the episode id so a rerun makes the same choice, matching how playback
    collapses the non-canonical rows of one episode.
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
def _report_unresolvable(session: Session, watch_identifiers: set[str]) -> None:
    """Log why the watches on `watch_identifiers` have nothing to be pointed at.

    A watch outlives the episode it names, so it can name one this database has
    never held, and there is nothing a rerun will do about it until that episode
    is imported. Saying which of the two it is separates a library that has yet
    to catch up from an episode that was deleted and is still there to restore.
    """
    if not watch_identifiers:
        return

    canonical_link = canonical_episode_link()
    named = _named_episodes(watch_identifiers)
    soft_deleted = set(
        session.exec(
            select(named.c.watch_identifier)
            .select_from(Episode)
            .join(canonical_link, links_of(Episode, canonical_link))
            .join(
                named,
                col(canonical_link.canonical_episode_id)
                == named.c.canonical_episode_id,
            )
            .where(is_non_canonical(Episode)),
        ).all(),
    )
    unknown = watch_identifiers - soft_deleted
    logger.info(
        "{} episodes have only a deleted link, {} have no link at all",
        len(soft_deleted),
        len(unknown),
    )
    if unknown:
        logger.info(
            "Episodes with no link, first few: {}",
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
    watch_identifiers = {watch.watch_identifier for watch in detached}
    candidates = _candidates_by_watch_identifier(session, watch_identifiers)
    _report_unresolvable(session, watch_identifiers - candidates.keys())
    configs: dict[UUID, SourceDedupConfig] = {}

    relinked = 0
    for watch in detached:
        matches = candidates.get(watch.watch_identifier)
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
            watch.watch_identifier,
        )

    session.commit()
    logger.info("Relinked {} of {} detached watches", relinked, len(detached))
    return relinked


if __name__ == "__main__":
    with Session(engine) as session:
        relink_watches(session)
