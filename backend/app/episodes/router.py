from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import UserEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePatchInput,
)
from app.media.service import create_record, delete_record, update_record
from app.models import Message
from app.watches.dependencies import ExistingEpisode
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreateInput,
    WatchInput,
    WatchOutput,
    WatchPostInput,
)

router = APIRouter(prefix="/episodes", tags=["episodes"])


# FAST003 - Parameter is used by ExistingEpisode.
@router.post("/{episode_id}/watches", response_model=WatchOutput)  # noqa: FAST003
def create_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode: ExistingEpisode,
    watch_input: WatchPostInput,
) -> Watch:
    """Create a new episode watch entry."""
    create_input = WatchCreateInput(user_id=current_user.id, **watch_input.model_dump())
    return create_record(
        session=session,
        parent=episode,
        post_input=create_input,
        input_schema=WatchInput,
    )


# FAST003 - Parameter is used by UserEpisode.
@router.get("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003
def get_user_episode(episode: UserEpisode) -> Episode:
    """Get an episode owned by the current user by its id."""
    return episode


# FAST003 - Parameter is used by UserEpisode.
@router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003
def update_user_episode(
    session: SessionDep,
    episode: UserEpisode,
    episode_input: EpisodePatchInput,
) -> Episode:
    """Update an episode by its id."""
    return update_record(session=session, entry=episode, body=episode_input)


# FAST003 - Parameter is used by UserEpisode.
@router.delete("/{episode_id}")  # noqa: FAST003
def delete_user_episode(session: SessionDep, episode: UserEpisode) -> Message:
    """Delete an episode by its id."""
    return delete_record(session=session, entry=episode, model_name="Episode")
