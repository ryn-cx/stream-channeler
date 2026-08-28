# TODO: Validate
import uuid

from sqlmodel import Session

from app.files.models import File
from app.plugins.models import Plugin
from app.users.models import User
from tests.app.helpers.utils import build_random_model
from tests.app.plugins.utils import create_random_plugin
from tests.app.users.utils import CreatedUser


# TODO: Validate
def create_random_file(
    session: Session,
    parent: Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> File:
    """Create a random `File` record in the database."""
    if not isinstance(parent, Plugin):
        parent = create_random_plugin(session)
    file = build_random_model(File, plugin_id=parent.id, deleted_at=None, **kwargs)
    session.add(file)
    session.flush()  # Allows file.plugin to be accessed.
    return file
