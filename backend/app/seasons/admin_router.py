# TODO: Validate


"""Season router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import ExistingSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonListOutput,
    SeasonOutput,
    SeasonsPublic,
    SeasonUpdate,
)
from app.service import list_response
from app.shows.dependencies import ExistingShow
from app.shows.models import Show
from app.sources.models import Source

seasons_router = APIRouter(
    prefix="/seasons",
    tags=["seasons"],
    dependencies=[Depends(get_current_active_superuser)],
)


show_seasons_router = APIRouter(
    prefix="/shows/{show_id}",
    tags=["seasons"],
    dependencies=[Depends(get_current_active_superuser)],
)


SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


# TODO: Validate
@show_seasons_router.post("/seasons")
def create_season(
    session: SessionDep,
    show: ExistingShow,
    season_input: SeasonCreate,
) -> SeasonOutput:
    return SeasonOutput.model_validate(season_input.create(session, Season, show))


# TODO: Validate
@seasons_router.get("")
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get `Season`s."""
    seasons = list_response(
        session=session,
        base=Season.select_with_plugin_eager(),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
    return seasons


# TODO: Validate
@seasons_router.get(
    "/{season_id}",
)
def get_season(season: ExistingSeason) -> SeasonOutput:
    return SeasonOutput.model_validate(season)


# TODO: Validate
@seasons_router.patch(
    "/{season_id}",
)
def update_season(
    session: SessionDep,
    season: ExistingSeason,
    season_input: SeasonUpdate,
) -> SeasonOutput:
    return SeasonOutput.model_validate(season_input.update(session, season))


# TODO: Validate
@seasons_router.delete(
    "/{season_id}",
)
def delete_season(session: SessionDep, season: ExistingSeason) -> Message:
    return delete_record(session, season)


router = APIRouter()
router.include_router(seasons_router)
router.include_router(show_seasons_router)
