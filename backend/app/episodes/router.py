"""Episodes router."""

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import OwnedEpisode, ReadableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodeUpdate,
)
from app.media.service import delete_record
from app.schemas import Message
from app.watches.schemas import (
    WatchCreate,
    WatchOutput,
)
from app.watches.services import create_watches

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by ReadableEpisode.
def get_episode(episode: ReadableEpisode) -> Episode:
    """Get an `Episode` if it's readable by the current `User`."""
    return episode


@router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by OwnedEpisode.
def update_episode(
    session: SessionDep,
    episode: OwnedEpisode,
    episode_input: EpisodeUpdate,
) -> Episode:
    """Update and return an `Episode` if it's owned by the current `User`."""
    return episode_input.update(session, episode)


@router.delete("/{episode_id}")  # noqa: FAST003 - Used by OwnedEpisode.
def delete_episode(session: SessionDep, episode: OwnedEpisode) -> Message:
    """Delete an `Episode` if it's owned by the current `User`."""
    return delete_record(session, episode)


@router.post("/{episode_id}/watches")  # noqa: FAST003 - Used by ReadableEpisode.
def create_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode: ReadableEpisode,
    watch_input: WatchCreate,
) -> list[WatchOutput]:
    """Create a `Watch` if the `Episode` is owned by the current `User`."""
    return create_watches(session, current_user.id, episode, watch_input)
