import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.media.service import get_first_or_error


def get_user_episode(
    session: SessionDep,
    current_user: CurrentUser,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    """Look up an episode by its UUID id and verify user ownership."""
    statement = select(Episode).where(Episode.id == episode_id)
    return get_first_or_error(session, statement, current_user.id, "Episode")


UserEpisode = Annotated[Episode, Depends(get_user_episode)]
