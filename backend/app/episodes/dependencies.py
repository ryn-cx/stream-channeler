import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.media.service import get_owned_record, get_readable_record
from app.users.dependencies import OptionalUser


def require_readable_episode(
    session: SessionDep,
    optional_user: OptionalUser,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    return get_readable_record(session, Episode, episode_id, optional_user)


def require_owned_episode(
    session: SessionDep,
    current_user: CurrentUser,
    episode_id: Annotated[uuid.UUID, Path()],
) -> Episode:
    return get_owned_record(session, Episode, episode_id, current_user.id)


ReadableEpisode = Annotated[Episode, Depends(require_readable_episode)]
OwnedEpisode = Annotated[Episode, Depends(require_owned_episode)]
