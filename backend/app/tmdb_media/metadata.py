# TODO: Validate

from collections.abc import Sequence
from typing import Any
from uuid import UUID

from sqlalchemy.orm import aliased
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.models import MediaMixin
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.episodes import links_of, tmdb_episode_link
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.tmdb import (
    parse_episode_extra,
    tmdb_episode_url,
)

# The three merged media models, named by the base they share so a level is
# something to pass rather than something to branch on.
type MediaModel = type[MediaMixin[Any]]

EPISODE_FIELDS = (
    "name",
    "description",
    "image_url",
    "thumbnail_url",
    "duration",
    "air_date",
)

EPISODE_ID_FIELD = "tmdb_episode_id"

TMDB_SEASON_NUMBER_FIELD = "tmdb_season_number"
TMDB_SEASON_NAME_FIELD = "tmdb_season_name"
TMDB_EPISODE_NUMBER_FIELD = "tmdb_episode_number"
TMDB_URL_FIELD = "tmdb_url"


# TODO: Validate
def _tmdb_rows(
    session: Session,
    rows: Sequence[Any],
    id_field: str,
    model: MediaModel,
) -> dict[UUID, Any]:
    """Load the canonical row each of `rows` points at, keyed by its id."""
    ids = {
        getattr(row, id_field, None)
        for row in rows
        if getattr(row, id_field, None) is not None
    }
    if not ids:
        return {}
    return {
        record.id: record
        for record in session.exec(
            select(model).where(is_not_linked(model), col(model.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def _seasons_of(
    session: Session,
    tmdb_episodes: Any,  # noqa: ANN401 - Any iterable of `Episode`.
) -> dict[UUID, Season]:
    ids = {episode.season_id for episode in tmdb_episodes}
    if not ids:
        return {}
    return {
        season.id: season
        for season in session.exec(
            select(Season).where(col(Season.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def _titles_of(
    session: Session,
    tmdb_seasons: Any,  # noqa: ANN401 - Any iterable of `Season`.
) -> dict[UUID, Title]:
    ids = {season.title_id for season in tmdb_seasons}
    if not ids:
        return {}
    return {
        title.id: title
        for title in session.exec(
            select(Title).where(is_not_linked(Title), col(Title.id).in_(ids)),
        ).all()
    }


# TODO: Validate
def serve_as_tmdb_episodes[RowT](
    session: Session,
    rows: Sequence[RowT],
) -> Sequence[RowT]:
    tmdb_rows = _tmdb_rows(session, rows, EPISODE_ID_FIELD, Episode)
    seasons = _seasons_of(session, tmdb_rows.values())
    titles = _titles_of(session, seasons.values())
    for row in rows:
        canonical = tmdb_rows.get(getattr(row, EPISODE_ID_FIELD, None))
        if canonical is None:
            continue
        for field in EPISODE_FIELDS:
            setattr(row, field, getattr(canonical, field))
        season = seasons.get(canonical.season_id)
        title = titles.get(season.title_id) if season else None
        setattr(row, TMDB_EPISODE_NUMBER_FIELD, canonical.episode_number)
        setattr(
            row,
            TMDB_SEASON_NUMBER_FIELD,
            season.season_number if season else None,
        )
        setattr(row, TMDB_SEASON_NAME_FIELD, season.name if season else None)
        native_season, native_episode = native_numbering(canonical, season)
        setattr(
            row,
            TMDB_URL_FIELD,
            tmdb_episode_url(
                title.key if title else None,
                native_season,
                native_episode,
            ),
        )
    return rows


# TODO: Validate
def native_numbering(
    tmdb_episode: Episode,
    season: Season | None,
) -> tuple[int | None, int | None]:
    native = parse_episode_extra(tmdb_episode.extra)
    season_number = (
        native.tmdb_season_number
        if native.tmdb_season_number is not None
        else (season.season_number if season else None)
    )
    episode_number = (
        native.tmdb_episode_number
        if native.tmdb_episode_number is not None
        else tmdb_episode.episode_number
    )
    return season_number, episode_number


# TODO: Validate
def tmdb_episode_of(
    session: Session,
    tmdb_episode_id: UUID | None,
) -> tuple[Episode, Season, Title] | None:
    """Return the episode a non-canonical row is of, with the season and title above it.

    A non-canonical row that is not of anything yet has nothing to return, which is the
    one case a caller has to handle; media TMDB has never heard of has a canonical row
    like any other.
    """
    if tmdb_episode_id is None:
        return None
    return session.exec(
        select(Episode, Season, Title)
        .join(
            Season,
            onclause=col(Episode.season_id) == Season.id,
        )
        .join(
            Title,
            onclause=col(Season.title_id) == Title.id,
        )
        .where(
            is_not_linked(Episode),
            is_not_linked(Title),
            Episode.id == tmdb_episode_id,
        ),
    ).first()


# TODO: Validate
def tmdb_season_of(
    session: Session,
    season_id: UUID,
) -> tuple[Season, Title] | None:
    copy_episode = aliased(Episode)
    tmdb_episode = aliased(Episode)
    copy_link = tmdb_episode_link()
    return session.exec(
        select(Season, Title)
        .select_from(copy_episode)
        .join(copy_link, links_of(copy_episode, copy_link))
        .join(
            tmdb_episode,
            onclause=col(copy_link.tmdb_episode_id) == tmdb_episode.id,
        )
        .join(Season, onclause=col(tmdb_episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .where(
            is_not_linked(Title),
            col(copy_episode.season_id) == season_id,
            col(copy_episode.deleted_at).is_(None),
        ),
    ).first()


# TODO: Validate
def tmdb_title_of(session: Session, title: Title) -> Title | None:
    tmdb_title_id = title.sole_tmdb_title_id
    if tmdb_title_id is None:
        return None
    return session.exec(
        select(Title).where(is_not_linked(Title), Title.id == tmdb_title_id),
    ).first()
