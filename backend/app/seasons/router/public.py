# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.episodes.schemas import EpisodeOutput
from app.seasons.dependencies import ExistingSeason
from app.seasons.schemas import (
    SeasonInformationOutput,
)
from app.seasons.service.information import season_information
from app.seasons.service.listing import season_episodes

"""Season router."""


seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])


# TODO: Validate
@seasons_router.get("/{season_id}/information")  # noqa: FAST003 - Used by ExistingSeason.
def get_season_information(
    session: SessionDep,
    season: ExistingSeason,
) -> SeasonInformationOutput:
    """Return canonical and non-canonical season informtion."""
    return season_information(session, season)


# TODO: Validate
@seasons_router.get("/{season_id}/episodes")  # noqa: FAST003 - Used by ExistingSeason.
def get_season_episodes(season: ExistingSeason) -> list[EpisodeOutput]:
    """Return every `Episode` a `Season` holds."""
    return season_episodes(season)


router = APIRouter()


router.include_router(seasons_router)
