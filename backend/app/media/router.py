# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, SessionDep
from app.constants import MAX_ENTRIES_PER_PAGE
from app.media.dependencies import ExistingEpisode, ExistingEpisodeWatch
from app.media.models import EpisodeWatch
from app.media.schemas import (
    EpisodeWatchPatchInput,
    EpisodeWatchPostInput,
    SingleEpisodeWatchOutput,
    WatchedEpisodesOutput,
)
from app.media.services import get_watched_episodes as get_watched_episodes_service
from app.media.services import save_episode_watch
from app.models import Message

router = APIRouter(prefix="/media", tags=["media"])


@router.post("/episode-watches")
def post_watched_episode(
    session: SessionDep,
    current_user: CurrentUser,
    watch_input: EpisodeWatchPostInput,
    episode: ExistingEpisode,
) -> SingleEpisodeWatchOutput:
    """Create a new episode watch entry."""
    episode_watch = EpisodeWatch(
        user_id=current_user.id,
        episode_id=watch_input.episode_id,
    )
    session.add(episode_watch)

    return save_episode_watch(
        session,
        episode_watch,
        episode,
        watch_input,
    )


# FAST003 - Parameter is used by EpisodeWatchDep
@router.patch("/episode-watches/{episode_watch_id}")  # noqa: FAST003
def patch_watched_episode(
    session: SessionDep,
    episode_watch: ExistingEpisodeWatch,
    watch_input: EpisodeWatchPatchInput,
) -> SingleEpisodeWatchOutput:
    """Update an existing episode watch entry."""
    return save_episode_watch(
        session,
        episode_watch,
        episode_watch.episode,
        watch_input,
    )


# FAST003 - Parameter is used by EpisodeWatchDep
@router.delete("/episode-watches/{episode_watch_id}")  # noqa: FAST003
def delete_watched_episode(
    session: SessionDep,
    episode_watch: ExistingEpisodeWatch,
) -> Message:
    """Delete an existing episode watch entry."""
    session.delete(episode_watch)
    session.commit()
    return Message(message="Episode watch deleted")


@router.get("/episode-watches")
def get_watched_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = MAX_ENTRIES_PER_PAGE,
) -> WatchedEpisodesOutput:
    """Get multiple watched episode entries."""
    return get_watched_episodes_service(session, current_user.id, skip, limit)
