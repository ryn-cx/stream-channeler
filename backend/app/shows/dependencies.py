import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_first_or_error
from app.shows.models import Show


def get_user_show(
    session: SessionDep,
    current_user: CurrentUser,
    show_id: Annotated[uuid.UUID, Path()],
) -> Show:
    """Look up a show by its UUID id and verify user ownership."""
    statement = select(Show).where(Show.id == show_id)
    return get_first_or_error(session, statement, current_user.id, "Show")


UserShow = Annotated[Show, Depends(get_user_show)]
