# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.episodes.dependencies import (
    AdminTmdbEpisode,
    ExistingEpisode,
)
from app.episodes.schemas import (
    TmdbEpisodeRecord,
    UserEpisodeUrlInput,
    UserEpisodeUrlOutput,
)
from app.episodes.service.information import tmdb_episode_record
from app.episodes.service.urls import (
    clear_episode_url_for_user,
    set_episode_url_for_user,
)

"""Episodes router."""


tmdb_episodes_router = APIRouter(
    prefix="/episodes/tmdb",
    tags=["tmdb-episodes"],
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
@tmdb_episodes_router.get("/{tmdb_episode_id}")  # noqa: FAST003 - Used by AdminTmdbEpisode.
def get_tmdb_episode_by_id(
    session: SessionDep,
    tmdb_episode: AdminTmdbEpisode,
) -> TmdbEpisodeRecord:
    """Get a `Episode`, with the season and title above it."""
    return tmdb_episode_record(session, tmdb_episode)


router = APIRouter()


router.include_router(tmdb_episodes_router)


router.include_router(episodes_router)
