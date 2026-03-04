import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_first_or_error
from app.plugins.models import Plugin


def get_user_plugin_by_id(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_id: Annotated[uuid.UUID, Path()],
) -> Plugin:
    """Get a plugin by its UUID id, verifying user ownership."""
    statement = select(Plugin).where(Plugin.id == plugin_id)
    return get_first_or_error(session, statement, current_user.id, "Plugin")


UserPlugin = Annotated[Plugin, Depends(get_user_plugin_by_id)]
