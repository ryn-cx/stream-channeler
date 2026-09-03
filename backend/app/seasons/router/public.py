# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.seasons.dependencies import ExistingSeason
from app.seasons.schemas import (
    SeasonInformationOutput,
)
from app.seasons.service import season_information

"""Season router."""


seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])


# TODO: Validate
@seasons_router.get("/{season_id}/information")  # noqa: FAST003 - Used by ExistingSeason.
def get_season_information(
    session: SessionDep,
    season: ExistingSeason,
) -> SeasonInformationOutput:
    """Return what the website and TMDB each say about a `Season`."""
    return season_information(session, season)


router = APIRouter()


router.include_router(seasons_router)
