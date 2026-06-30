# TODO: Validate
"""Season router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import OwnedSeason, ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
    SeasonsPublic,
    SeasonUpdate,
)
from app.service import get_read_results
from app.shows.dependencies import OwnedShow, ReadableShow
from app.shows.models import Show
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.service import get_or_create_plugin_user

seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])


@seasons_router.get("")
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SeasonsPublic:
    season_selector = select(Season).join(Show).join(Source).join(Plugin)
    if read_options.owner is None:
        season_selector = season_selector.where(Plugin.user_id == current_user.id)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        plugin_user = get_or_create_plugin_user(session=session)
        if read_options.owner == MediaOwner.official:
            season_selector = season_selector.where(Plugin.user_id == plugin_user.id)
        else:
            season_selector = season_selector.where(
                col(Plugin.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        season_selector,
        schema=SeasonOutput,
        default_sort=Season.created_at,
        tiebreaker=Season.id,
        params=read_options,
        current_user=current_user,
    )
    return SeasonsPublic(
        data=[SeasonOutput.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


@seasons_router.get("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003 - Used by ReadableSeason
def get_season(season: ReadableSeason) -> Season:
    """Get a `Season` if it's readable by the current `User`."""
    return season


@seasons_router.patch("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003 - Used by OwnedSeason
def update_season(
    session: SessionDep,
    season: OwnedSeason,
    season_input: SeasonUpdate,
) -> Season:
    """Update and return a `Season` if it's owned by the current `User`."""
    return season_input.update(session, season)


@seasons_router.delete("/{season_id}")  # noqa: FAST003 - Used by OwnedSeason
def delete_season(session: SessionDep, season: OwnedSeason) -> Message:
    """Delete a `Season` if it's owned by the current `User`."""
    return delete_record(session, season)


show_seasons_router = APIRouter(prefix="/shows/{show_id}", tags=["seasons"])


@show_seasons_router.post("/seasons", response_model=SeasonOutput)
def create_season(
    session: SessionDep,
    show: OwnedShow,
    season_input: SeasonCreate,
) -> Season:
    """Create a `Season` if the `Show` is owned by the current `User`."""
    return season_input.create(session, Season, show)


@show_seasons_router.get("/seasons")
def get_show_seasons(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """List all `Season`s for a `Show` if it's readable by the current `User`."""
    base = select(Season).where(Season.show_id == show.id)
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=SeasonOutput,
        default_sort=Season.created_at,
        tiebreaker=Season.id,
        params=read_options,
        current_user=current_user,
    )
    return SeasonsPublic(
        data=[SeasonOutput.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


router = APIRouter()
router.include_router(seasons_router)
router.include_router(show_seasons_router)
