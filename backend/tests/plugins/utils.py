# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.users.models import User
from tests.users.utils import CreatedUser, create_random_user
from tests.utils.utils import build_random_model

PluginParent = User | CreatedUser | uuid.UUID


def create_random_plugin(
    db: Session,
    parent: User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Plugin:
    if parent is None:
        parent = create_random_user(db)
    if isinstance(parent, (User, CreatedUser)):
        parent = parent.id
    plugin = build_random_model(Plugin, user_id=parent, deleted_at=None, **kwargs)
    db.add(plugin)
    db.flush()  # Allows plugin.user, plugin.sources, and plugin.files to be accessed.
    return plugin
