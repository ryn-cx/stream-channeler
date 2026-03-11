import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_readable_resource, get_user_resource
from app.plugins.models import Plugin
from app.users.dependencies import OptionalUser


def require_user_plugin_by_id(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_id: Annotated[uuid.UUID, Path()],
) -> Plugin:
    return get_user_resource(session, Plugin, plugin_id, current_user.id)


UserPlugin = Annotated[Plugin, Depends(require_user_plugin_by_id)]


def require_readable_plugin(
    session: SessionDep,
    optional_user: OptionalUser,
    plugin_id: Annotated[uuid.UUID, Path()],
) -> Plugin:
    return get_readable_resource(session, Plugin, plugin_id, optional_user)


ReadablePlugin = Annotated[Plugin, Depends(require_readable_plugin)]
