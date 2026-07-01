"""Season router."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_list_response,
    media_owner_list_response,
)
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import EditableSeason, ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
    SeasonsPublic,
    SeasonUpdate,
)
from app.shows.dependencies import EditableShow, ReadableShow
from app.shows.models import Show
from app.sources.models import Source
from app.users.dependencies import OptionalUser

show_seasons_router = APIRouter(prefix="/shows/{show_id}", tags=["seasons"])
seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])


@show_seasons_router.post("/seasons", response_model=SeasonOutput)
def create_season(
    session: SessionDep,
    show: EditableShow,
    season_input: SeasonCreate,
) -> Season:
    """Create a `Season` if the `Show` is editable by the `User`."""
    return season_input.create(session, Season, show)


@seasons_router.get("")
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SeasonsPublic:
    """Get all of the `Season`s readable by the `User`."""
    return media_owner_list_response(
        session=session,
        base=select(Season).join(Show).join(Source).join(Plugin),
        response_model=SeasonsPublic,
        schema=SeasonOutput,
        read_options=read_options,
        current_user=current_user,
    )


@show_seasons_router.get("/seasons")
def get_show_seasons(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get all of the `Season`s for a `Show` if it is readable by the `User`."""
    base = select(Season).where(Season.show_id == show.id)
    return media_list_response(
        session=session,
        base=base,
        response_model=SeasonsPublic,
        schema=SeasonOutput,
        params=read_options,
        current_user=current_user,
    )


@seasons_router.get("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003 - Used by ReadableSeason
def get_season(season: ReadableSeason) -> Season:
    """Get a `Season` if it's readable by the `User`."""
    return season


@seasons_router.patch("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003 - Used by EditableSeason
def update_season(
    session: SessionDep,
    season: EditableSeason,
    season_input: SeasonUpdate,
) -> Season:
    """Update and return a `Season` if it's editable by the `User`."""
    return season_input.update(session, season)


@seasons_router.delete("/{season_id}")  # noqa: FAST003 - Used by EditableSeason
def delete_season(session: SessionDep, season: EditableSeason) -> Message:
    """Delete a `Season` if it's editable by the `User`."""
    return delete_record(session, season)


router = APIRouter()
router.include_router(seasons_router)
router.include_router(show_seasons_router)
