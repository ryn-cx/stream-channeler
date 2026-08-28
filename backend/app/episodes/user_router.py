# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.episodes.dependencies import (
    AdminCanonicalEpisode,
    ExistingEpisode,
)
from app.episodes.schemas import (
    CanonicalEpisodeRecord,
    UserEpisodeUrlInput,
    UserEpisodeUrlOutput,
)
from app.episodes.service import (
    canonical_episode_record,
    clear_episode_url_for_user,
    set_episode_url_for_user,
)

"""Episodes router."""


canonical_episodes_router = APIRouter(
    prefix="/episodes/canonical",
    tags=["canonical-episodes"],
)


episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])


# TODO: Validate
@episodes_router.put("/{episode_id}/user-url")  # noqa: FAST003 - Used by ExistingEpisode.
def set_episode_user_url(
    session: SessionDep,
    episode: ExistingEpisode,
    current_user: CurrentUser,
    url_input: UserEpisodeUrlInput,
) -> UserEpisodeUrlOutput:
    return set_episode_url_for_user(session, episode, current_user, url_input.url)


# TODO: Validate
@episodes_router.delete("/{episode_id}/user-url")  # noqa: FAST003 - Used by ExistingEpisode.
def delete_episode_user_url(
    session: SessionDep,
    episode: ExistingEpisode,
    current_user: CurrentUser,
) -> UserEpisodeUrlOutput:
    return clear_episode_url_for_user(session, episode, current_user)


# TODO: Validate
@canonical_episodes_router.get("/{canonical_episode_id}")  # noqa: FAST003 - Used by AdminCanonicalEpisode.
def get_canonical_episode_by_id(
    session: SessionDep,
    canonical_episode: AdminCanonicalEpisode,
) -> CanonicalEpisodeRecord:
    """Get a `Episode`, with the season and title above it."""
    return canonical_episode_record(session, canonical_episode)


router = APIRouter()


router.include_router(canonical_episodes_router)


router.include_router(episodes_router)
