"""Dependencies for watch-related media."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.media.service import get_first_or_error
from app.watches.models import Watch


def get_user_watch(
    session: SessionDep,
    current_user: CurrentUser,
    watch_id: Annotated[uuid.UUID, Path()],
) -> Watch:
    """Look up a watch by its UUID id and verify user ownership."""
    statement = select(Watch).where(Watch.id == watch_id)
    return get_first_or_error(session, statement, current_user.id, "Watch")


UserWatch = Annotated[Watch, Depends(get_user_watch)]


def get_existing_episode(
    session: SessionDep,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    """Get an episode if it exists."""
    statement = select(Episode).where(Episode.id == episode_id)
    episode = session.exec(statement).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    return episode


ExistingEpisode = Annotated[Episode, Depends(get_existing_episode)]
