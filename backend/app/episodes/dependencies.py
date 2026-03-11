# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.media.service import get_readable_resource, get_user_resource
from app.users.dependencies import OptionalUser


def require_user_episode(
    session: SessionDep,
    current_user: CurrentUser,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    return get_user_resource(session, Episode, episode_id, current_user.id)


UserEpisode = Annotated[Episode, Depends(require_user_episode)]


def require_readable_episode(
    session: SessionDep,
    optional_user: OptionalUser,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    return get_readable_resource(session, Episode, episode_id, optional_user)


ReadableEpisode = Annotated[Episode, Depends(require_readable_episode)]
