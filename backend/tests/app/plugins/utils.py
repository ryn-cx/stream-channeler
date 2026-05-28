# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.users.models import User
from tests.app.users.utils import CreatedUser, create_random_user
from tests.app.utils.utils import build_random_model

PluginParent = User | CreatedUser | uuid.UUID


def create_random_plugin(
    session: Session,
    parent: User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Plugin:
    if parent is None:
        parent = create_random_user(session)
    if isinstance(parent, (User, CreatedUser)):
        parent = parent.id
    plugin = build_random_model(Plugin, user_id=parent, deleted_at=None, **kwargs)
    session.add(plugin)
    session.flush()  # Allows plugin.user, plugin.sources, and plugin.files to be accessed.
    return plugin
