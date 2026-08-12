# TODO: Validate
"""Canonical season router. Admin-only, as every canonical endpoint is."""

from typing import Annotated, Any

from fastapi import APIRouter, Query
from sqlalchemy.orm import contains_eager
from sqlmodel import col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_media.dependencies import AdminCanonicalSeason, AdminCanonicalShow
from app.canonical_media.read import canonical_list_response
from app.canonical_seasons.models import CanonicalSeason
from app.canonical_seasons.schemas import (
    CanonicalSeasonListOutput,
    CanonicalSeasonOutput,
    CanonicalSeasonsPublic,
)
from app.canonical_shows.models import CanonicalShow
from app.schemas import ReadOptions

canonical_show_seasons_router = APIRouter(
    prefix="/canonical-shows/{canonical_show_id}",
    tags=["canonical-seasons"],
)
canonical_seasons_router = APIRouter(
    prefix="/canonical-seasons",
    tags=["canonical-seasons"],
)

CANONICAL_SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "canonical_show_name": CanonicalShow.name,
    "canonical_show_key": CanonicalShow.key,
}


# TODO: Validate
def _select_with_show() -> SelectOfScalar[CanonicalSeason]:
    """Select seasons with the title above each one already loaded.

    Joined rather than left to load itself, since the title's name is a column
    of the list and a row at a time would be a query at a time.
    """
    return (
        select(CanonicalSeason)
        .join(
            CanonicalShow,
            onclause=col(CanonicalSeason.canonical_show_id) == CanonicalShow.id,
        )
        .options(contains_eager(CanonicalSeason.canonical_show))  # type: ignore[arg-type]
    )


# TODO: Validate
@canonical_seasons_router.get("")
def get_canonical_seasons(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalSeasonsPublic:
    """Get every `CanonicalSeason`."""
    return canonical_list_response(
        session=session,
        base=_select_with_show(),
        response_model=CanonicalSeasonsPublic,
        schema=CanonicalSeasonListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_SEASON_EXTRA_COLUMNS,
    )


# TODO: Validate
@canonical_show_seasons_router.get("/canonical-seasons")
def get_canonical_show_seasons(
    session: SessionDep,
    canonical_show: AdminCanonicalShow,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalSeasonsPublic:
    """Get every `CanonicalSeason` of one `CanonicalShow`."""
    return canonical_list_response(
        session=session,
        base=_select_with_show().where(
            CanonicalSeason.canonical_show_id == canonical_show.id,
        ),
        response_model=CanonicalSeasonsPublic,
        schema=CanonicalSeasonListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=CANONICAL_SEASON_EXTRA_COLUMNS,
    )


# TODO: Validate
@canonical_seasons_router.get("/{canonical_season_id}")  # noqa: FAST003 - Used by AdminCanonicalSeason.
def get_canonical_season_by_id(
    canonical_season: AdminCanonicalSeason,
) -> CanonicalSeasonOutput:
    """Get a `CanonicalSeason`."""
    return CanonicalSeasonOutput.model_validate(canonical_season)


router = APIRouter()
router.include_router(canonical_seasons_router)
router.include_router(canonical_show_seasons_router)
