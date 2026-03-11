import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.media.service import get_user_resource
from app.watches.models import Watch


def require_user_watch(
    session: SessionDep,
    current_user: CurrentUser,
    watch_id: Annotated[uuid.UUID, Path()],
) -> Watch:
    return get_user_resource(session, Watch, watch_id, current_user.id)


UserWatch = Annotated[Watch, Depends(require_user_watch)]


def require_existing_episode(
    session: SessionDep,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    """Get an episode if it exists."""
    statement = select(Episode).where(Episode.id == episode_id)
    episode = session.exec(statement).first()

    if not episode:
        raise HTTPException(status_code=404, detail="Episode not found")

    return episode


ExistingEpisode = Annotated[Episode, Depends(require_existing_episode)]
