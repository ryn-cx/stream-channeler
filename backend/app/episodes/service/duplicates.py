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
    EpisodeTmdbEpisode,
)
from app.episodes.schemas import (
    DuplicatedTmdbEpisodeOutput,
    EpisodeRecord,
)
from app.episodes.service.records import _record_fields
from app.seasons.models import Season
from app.sources.models import Source
from app.sources.schemas import SourceListPublic
from app.titles.models import Title


# TODO: Validate
def _duplicated_link_pairs(
    session: Session,
    limit: int,
) -> list[tuple[uuid.UUID, uuid.UUID]]:
    uses = func.count(col(EpisodeTmdbEpisode.episode_id).distinct())
    unsettled = func.bool_or(col(Episode.tmdb_episode_validated_at).is_(None))
    statement = (
        select(
            col(EpisodeTmdbEpisode.tmdb_episode_id),
            col(Title.source_id),
        )
        .join(Episode, onclause=col(EpisodeTmdbEpisode.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .where(
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
        )
        .group_by(
            col(EpisodeTmdbEpisode.tmdb_episode_id),
            col(Title.source_id),
        )
        .having(uses > 1, unsettled)
        .limit(limit)
    )
    return [
        (tmdb_record_id, source_id)
        for tmdb_record_id, source_id in session.exec(statement).all()
    ]


# TODO: Validate
def _episodes_linking_to(
    session: Session,
    pairs: Collection[tuple[uuid.UUID, uuid.UUID]],
) -> dict[tuple[uuid.UUID, uuid.UUID], list[EpisodeRecord]]:
    tmdb_episode_ids = {tmdb_record_id for tmdb_record_id, _source_id in pairs}
    statement = (
        select(  # type: ignore[call-overload]
            col(EpisodeTmdbEpisode.tmdb_episode_id),
            col(Title.source_id),
            Episode,
            Season,
            Title,
        )
        .join(Episode, onclause=col(EpisodeTmdbEpisode.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .where(
            col(EpisodeTmdbEpisode.tmdb_episode_id).in_(
                tmdb_episode_ids,
            ),
            col(Episode.deleted_at).is_(None),
            col(Season.deleted_at).is_(None),
            col(Title.deleted_at).is_(None),
        )
        .order_by(col(Season.season_number), col(Episode.episode_number))
    )
    wanted = set(pairs)
    linking: dict[
        tuple[uuid.UUID, uuid.UUID],
        list[EpisodeRecord],
    ] = defaultdict(list)
    for tmdb_record_id, source_id, episode, season, title in session.exec(
        statement,
    ).all():
        if (tmdb_record_id, source_id) not in wanted:
            continue
        linking[tmdb_record_id, source_id].append(
            EpisodeRecord(**_record_fields(episode, season, title)),
        )
    return linking


# TODO: Validate
def get_duplicated_tmdb_episodes(
    session: Session,
    limit: int,
) -> list[DuplicatedTmdbEpisodeOutput]:
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
    tmdb_episodes = {
        episode.id: (episode, season, title, source)
        for episode, season, title, source in session.exec(
            select(Episode, Season, Title, Source)
            .join(Season, onclause=col(Episode.season_id) == Season.id)
            .join(Title, onclause=col(Season.title_id) == Title.id)
            .join(Source, onclause=col(Title.source_id) == Source.id)
            .where(col(Episode.id).in_({tmdb_record_id for tmdb_record_id, _ in pairs})),
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

    outputs: list[DuplicatedTmdbEpisodeOutput] = []
    for tmdb_record_id, source_id in pairs:
        found = tmdb_episodes.get(tmdb_record_id)
        source = sources.get(source_id)
        if found is None or source is None:
            continue
        episode, season, title, _tmdb_source = found
        outputs.append(
            DuplicatedTmdbEpisodeOutput(
                id=f"{episode.id}:{source.id}",
                tmdb=EpisodeRecord(**_record_fields(episode, season, title)),
                source=SourceListPublic.model_validate(source),
                linked_episodes=linking.get((tmdb_record_id, source_id), []),
            ),
        )
    return sorted(
        outputs,
        key=lambda output: (
            output.source.key,
            output.tmdb.title.name or "",
            output.tmdb.season.season_number or 0,
            output.tmdb.episode.episode_number or 0,
        ),
    )
