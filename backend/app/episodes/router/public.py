# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.episodes.dependencies import (
    ExistingEpisode,
)
from app.episodes.schemas import (
    EpisodeInformationOutput,
    EpisodeListOutput,
)
from app.episodes.service.information import episode_information, linked_episodes
from app.users.dependencies import OptionalUser

"""Episodes router."""


episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])


# TODO: Validate
@episodes_router.get("/{episode_id}/information")  # noqa: FAST003 - Used by ExistingEpisode.
def get_episode_information(
    session: SessionDep,
    episode: ExistingEpisode,
    user: OptionalUser,
) -> EpisodeInformationOutput:
    """Return what the website and TMDB each say about an `Episode`."""
    return episode_information(session, episode, user)


# TODO: Validate
@episodes_router.get(
    "/{episode_id}/linked",  # noqa: FAST003 - Used by ExistingEpisode.
)
def get_linked_episodes(episode: ExistingEpisode) -> list[EpisodeListOutput]:
    """Get every website's row standing for an `Episode`."""
    return linked_episodes(episode)


router = APIRouter()


router.include_router(episodes_router)
