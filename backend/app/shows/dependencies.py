# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_owned_record, get_readable_record
from app.shows.models import Show
from app.users.dependencies import OptionalUser


def require_readable_show(
    session: SessionDep,
    optional_user: OptionalUser,
    show_id: Annotated[uuid.UUID, Path()],
) -> Show:
    return get_readable_record(session, Show, show_id, optional_user)


def require_owned_show(
    session: SessionDep,
    current_user: CurrentUser,
    show_id: Annotated[uuid.UUID, Path()],
) -> Show:
    return get_owned_record(session, Show, show_id, current_user.id)


ReadableShow = Annotated[Show, Depends(require_readable_show)]
OwnedShow = Annotated[Show, Depends(require_owned_show)]
