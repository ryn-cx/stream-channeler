# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, Any, NewType

from sqlalchemy.orm import aliased, selectinload
from sqlmodel import col, select

from app.episodes.models import Episode, EpisodeTmdbEpisode
from app.episodes.service.names.forms import get_normalized_episode_name
from app.seasons.models import Season
from app.titles.models import Title, TitleTmdbTitle

if TYPE_CHECKING:
    import uuid
    from collections.abc import Sequence

    from sqlmodel import Session


LoadedTitle = NewType("LoadedTitle", Title)


# TODO: Validate
def other_source_filters(
    other_title: Any,  # noqa: ANN401 - An alias of `Title`.
    title_id: uuid.UUID,
    tmdb_title_ids: Sequence[uuid.UUID],
) -> tuple[Any, ...]:
    return (
        col(TitleTmdbTitle.tmdb_title_id).in_(tmdb_title_ids),
        other_title.id != title_id,
        other_title.deleted_at.is_(None),
        col(Season.deleted_at).is_(None),
        col(Episode.deleted_at).is_(None),
        col(Episode.name).is_not(None),
        col(Episode.episode_number).is_not(None),
    )


# TODO: Validate
def matching_episodes(
    session: Session,
    episode: Episode,
    title: Title,
    tmdb_title_ids: Sequence[uuid.UUID],
) -> list[Episode]:
    name = get_normalized_episode_name(episode.name, title.name)
    if not name or episode.episode_number is None or not tmdb_title_ids:
        return []
    other_title = aliased(Title)
    candidates = session.exec(
        select(Episode, col(other_title.name))
        .join(Season, onclause=col(Episode.season_id) == col(Season.id))
        .join(other_title, onclause=col(Season.title_id) == other_title.id)
        .join(
            TitleTmdbTitle,
            onclause=col(TitleTmdbTitle.title_id) == other_title.id,
        )
        .where(
            *other_source_filters(other_title, title.id, tmdb_title_ids),
            col(Episode.episode_number) == episode.episode_number,
        ),
    ).all()
    return [
        candidate
        for candidate, candidate_title_name in candidates
        if get_normalized_episode_name(candidate.name, candidate_title_name) == name
    ]


# TODO: Validate
def load_title_episodes(session: Session, title: Title) -> LoadedTitle:
    session.exec(
        select(Title)
        .where(col(Title.id) == title.id)
        .options(
            selectinload(Title.seasons)  # type: ignore[arg-type]
            .selectinload(Season.episodes)  # type: ignore[arg-type]
            .selectinload(Episode.tmdb_episode_links)  # type: ignore[arg-type]
            .selectinload(EpisodeTmdbEpisode.tmdb_episode),  # type: ignore[arg-type]
            selectinload(Title.tmdb_title_links)  # type: ignore[arg-type]
            .selectinload(TitleTmdbTitle.tmdb_title)  # type: ignore[arg-type]
            .selectinload(Title.seasons)  # type: ignore[arg-type]
            .selectinload(Season.episodes),  # type: ignore[arg-type]
        ),
    ).all()
    return LoadedTitle(title)


# TODO: Validate
def title_episodes(title: LoadedTitle) -> list[Episode]:
    return [
        episode
        for season in title.active_children
        for episode in season.active_children
    ]
