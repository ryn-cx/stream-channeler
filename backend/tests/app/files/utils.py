# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import File, Plugin
from app.users.models import User
from tests.app.plugins.utils import create_random_plugin
from tests.app.users.utils import CreatedUser
from tests.app.utils.utils import build_random_model


def create_random_file(
    session: Session,
    parent: Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> File:
    if not isinstance(parent, Plugin):
        parent = create_random_plugin(session, parent)
    file = build_random_model(File, plugin_id=parent.id, deleted_at=None, **kwargs)
    session.add(file)
    session.flush()  # Allows file.plugin to be accessed.
    return file
