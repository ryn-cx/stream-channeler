# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from tests.users.utils import create_random_user
from tests.utils.utils import build_random_model


def create_random_plugin(
    db: Session,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> Plugin:
    if user_id is None:
        user_id = create_random_user(db).id
    plugin = build_random_model(Plugin, user_id=user_id, deleted_at=None, **kwargs)
    db.add(plugin)
    # Flush so plugin.sources and plugin.files can be accessed.
    db.flush()
    return plugin
