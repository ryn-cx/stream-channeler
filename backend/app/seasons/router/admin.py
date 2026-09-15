# TODO: Validate


"""Season router."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.schemas import ReadOptions
from app.seasons.dependencies import ExistingSeason
from app.seasons.schemas import (
    SeasonOutput,
    SeasonsPublic,
)
from app.seasons.service.listing import season_list_output

seasons_router = APIRouter(
    prefix="/seasons",
    tags=["seasons"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@seasons_router.get("")
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """Get `Season`s."""
    return season_list_output(session, current_user, read_options)


# TODO: Validate
@seasons_router.get(
    "/{season_id}",
)
def get_season(season: ExistingSeason) -> SeasonOutput:
    return SeasonOutput.model_validate(season)


router = APIRouter()
router.include_router(seasons_router)
