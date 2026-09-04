# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

import uuid
from collections import defaultdict
from collections.abc import Collection

from sqlmodel import Session, col, func, select

from app.episodes.models import (
    Episode,
    EpisodeCanonicalEpisode,
)
from app.episodes.schemas import (
    DuplicatedCanonicalEpisodeOutput,
    EpisodeRecord,
)
from app.episodes.service.records import _record_fields
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.sources.schemas import SourceListPublic


# TODO: Validate
def _duplicated_link_pairs(
    session: Session,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    uses = func.count(col(EpisodeCanonicalEpisode.episode_id).distinct())
    unsettled = func.bool_or(col(Episode.canonical_episode_validated_at).is_(None))
    statement = (
        select(
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
        )
        .join(Episode, onclause=col(EpisodeCanonicalEpisode.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .group_by(
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
        )
        .having(uses > 1, unsettled)
        .limit(limit)
    )
    return [
        (canonical_id, source_id)
        for canonical_id, source_id in session.exec(statement).all()
    ]


# TODO: Validate
def _episodes_linking_to(
    session: Session,
    pairs: Collection[tuple[uuid.UUID, uuid.UUID]],
) -> dict[tuple[uuid.UUID, uuid.UUID], list[EpisodeRecord]]:
    canonical_episode_ids = {canonical_id for canonical_id, _source_id in pairs}
    statement = (
        select(  # type: ignore[call-overload]
            col(EpisodeCanonicalEpisode.canonical_episode_id),
            col(Show.source_id),
            Episode,
            Season,
            Show,
        )
        .join(Episode, onclause=col(EpisodeCanonicalEpisode.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .where(
            col(EpisodeCanonicalEpisode.canonical_episode_id).in_(
                canonical_episode_ids,
            ),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Show.deleted_at).is_(None),
        )
        .order_by(col(Season.season_number), col(Episode.episode_number))
    )
    wanted = set(pairs)
    linking: dict[
        tuple[uuid.UUID, uuid.UUID],
        list[EpisodeRecord],
    ] = defaultdict(list)
    for canonical_id, source_id, episode, season, show in session.exec(statement).all():
        if (canonical_id, source_id) not in wanted:
            continue
        linking[canonical_id, source_id].append(
            EpisodeRecord(**_record_fields(episode, season, show)),
        )
    return linking


# TODO: Validate
def get_duplicated_canonical_episodes(
    session: Session,
    limit: int,
) -> list[DuplicatedCanonicalEpisodeOutput]:
    """Return every canonical episode a single source points more than one episode at.

    Two episodes of one website standing for the same canonical episode is a
    link made wrongly rather than a title carried twice, so they are gathered by
    the canonical episode they collide on and served with the episodes that made
    the claim. Any provider's canonical rows are read, not only TMDB's.
    """
    pairs = _duplicated_link_pairs(session, limit)
    if not pairs:
        return []

    linking = _episodes_linking_to(session, pairs)
    canonical_episodes = {
        episode.id: (episode, season, show, source)
        for episode, season, show, source in session.exec(
            select(Episode, Season, Show, Source)
            .join(Season, onclause=col(Episode.season_id) == Season.id)
            .join(Show, onclause=col(Season.show_id) == Show.id)
            .join(Source, onclause=col(Show.source_id) == Source.id)
            .where(col(Episode.id).in_({canonical_id for canonical_id, _ in pairs})),
        ).all()
    }
    sources = {
        source.id: source
        for source in session.exec(
            select(Source).where(
                col(Source.id).in_({source_id for _, source_id in pairs}),
            ),
        ).all()
    }

    outputs: list[DuplicatedCanonicalEpisodeOutput] = []
    for canonical_id, source_id in pairs:
        found = canonical_episodes.get(canonical_id)
        source = sources.get(source_id)
        if found is None or source is None:
            continue
        episode, season, show, _canonical_source = found
        outputs.append(
            DuplicatedCanonicalEpisodeOutput(
                id=f"{episode.id}:{source.id}",
                canonical=EpisodeRecord(**_record_fields(episode, season, show)),
                source=SourceListPublic.model_validate(source),
                linked_episodes=linking.get((canonical_id, source_id), []),
            ),
        )
    return sorted(
        outputs,
        key=lambda output: (
            output.source.name or "",
            output.canonical.show.name or "",
            output.canonical.season.season_number or 0,
            output.canonical.episode.episode_number or 0,
        ),
    )
