# TODO: Validate
from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import ReadableEpisode, UserEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
)
from app.media.service import delete_record, update_record
from app.models import Message
from app.watches.schemas import (
    WatchOutput,
    WatchPostInput,
)
from app.watches.services import create_watches

router = APIRouter(prefix="/episodes", tags=["episodes"])


# FAST003 - Parameter is used by ReadableEpisode.
@router.post("/{episode_id}/watches")  # noqa: FAST003
def create_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode: ReadableEpisode,
    watch_input: WatchPostInput,
) -> list[WatchOutput]:
    """Create watch entries for an episode and all matching siblings."""
    return create_watches(session, current_user.id, episode, watch_input)


# FAST003 - Parameter is used by ReadableEpisode.
@router.get("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003
def get_user_episode(episode: ReadableEpisode) -> Episode:
    """Get an episode by its id if its plugin is public or owned by the current user."""
    return episode


# FAST003 - Parameter is used by UserEpisode.
@router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003
def update_user_episode(
    session: SessionDep,
    episode: UserEpisode,
    episode_input: EpisodePatchInput,
) -> Episode:
    """Update an episode by its id."""
    return update_record(session, episode, episode_input)


# FAST003 - Parameter is used by UserEpisode.
@router.delete("/{episode_id}")  # noqa: FAST003
def delete_user_episode(session: SessionDep, episode: UserEpisode) -> Message:
    """Delete an episode by its id."""
    return delete_record(session, episode)
