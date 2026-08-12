# TODO: Validate
"""Canonical episode router. Admin-only, as every canonical endpoint is."""

from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy.orm import contains_eager
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_episodes.models import CanonicalEpisode
from app.canonical_episodes.schemas import (
    CanonicalEpisodeListOutput,
    CanonicalEpisodeOutput,
    CanonicalEpisodesPublic,
)
from app.canonical_media.dependencies import (
    AdminCanonicalEpisode,
    AdminCanonicalSeason,
    AdminCanonicalShow,
)
from app.canonical_media.read import canonical_list_response
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_shows.models import CanonicalShow
from app.schemas import ReadOptions

canonical_show_episodes_router = APIRouter(
    prefix="/canonical-shows/{canonical_show_id}",
    tags=["canonical-episodes"],
)
canonical_season_episodes_router = APIRouter(
    prefix="/canonical-seasons/{canonical_season_id}",
    tags=["canonical-episodes"],
)
canonical_episodes_router = APIRouter(
    prefix="/canonical-episodes",
    tags=["canonical-episodes"],
)

CANONICAL_EPISODE_EXTRA_COLUMNS: dict[str, Any] = {
    "canonical_season_name": CanonicalSeason.name,
    "canonical_show_id": CanonicalSeason.canonical_show_id,
    "canonical_show_name": CanonicalShow.name,
    "canonical_show_key": CanonicalShow.key,
}


# TODO: Validate
def _select_with_season_and_show() -> SelectOfScalar[CanonicalEpisode]:
    """Select episodes with the season and title above each one already loaded."""
    return (
        select(CanonicalEpisode)
        .join(
            CanonicalSeason,
            onclause=col(CanonicalEpisode.canonical_season_id) == CanonicalSeason.id,
        )
        .join(
            CanonicalShow,
            onclause=col(CanonicalSeason.canonical_show_id) == CanonicalShow.id,
        )
        .options(
            contains_eager(CanonicalEpisode.canonical_season).contains_eager(  # type: ignore[arg-type]
                CanonicalSeason.canonical_show
            ),  # type: ignore[arg-type]
        )
    )


# TODO: Validate
@canonical_episodes_router.get("")
def get_canonical_episodes(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalEpisodesPublic:
    """Get every `CanonicalEpisode`."""
    return canonical_list_response(
        session=session,
        base=_select_with_season_and_show(),
        response_model=CanonicalEpisodesPublic,
        schema=CanonicalEpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_EPISODE_EXTRA_COLUMNS,
    )


# TODO: Validate
@canonical_season_episodes_router.get("/canonical-episodes")
def get_canonical_season_episodes(
    session: SessionDep,
    canonical_season: AdminCanonicalSeason,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalEpisodesPublic:
    """Get every `CanonicalEpisode` of one `CanonicalSeason`."""
    return canonical_list_response(
        session=session,
        base=_select_with_season_and_show().where(
            CanonicalEpisode.canonical_season_id == canonical_season.id,
        ),
        response_model=CanonicalEpisodesPublic,
        schema=CanonicalEpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_EPISODE_EXTRA_COLUMNS,
    )


# TODO: Validate
@canonical_show_episodes_router.get("/canonical-episodes")
def get_canonical_show_episodes(
    session: SessionDep,
    canonical_show: AdminCanonicalShow,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalEpisodesPublic:
    """Get every `CanonicalEpisode` under one `CanonicalShow`, across its seasons."""
    return canonical_list_response(
        session=session,
        base=_select_with_season_and_show().where(
            CanonicalSeason.canonical_show_id == canonical_show.id,
        ),
        response_model=CanonicalEpisodesPublic,
        schema=CanonicalEpisodeListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_EPISODE_EXTRA_COLUMNS,
    )


# TODO: Validate
@canonical_episodes_router.get("/{canonical_episode_id}")  # noqa: FAST003 - Used by AdminCanonicalEpisode.
def get_canonical_episode_by_id(
    canonical_episode: AdminCanonicalEpisode,
) -> CanonicalEpisodeOutput:
    """Get a `CanonicalEpisode`."""
    return CanonicalEpisodeOutput.model_validate(canonical_episode)


router = APIRouter()
router.include_router(canonical_episodes_router)
router.include_router(canonical_season_episodes_router)
router.include_router(canonical_show_episodes_router)
