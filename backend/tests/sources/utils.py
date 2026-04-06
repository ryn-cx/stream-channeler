# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from app.users.models import User
from tests.plugins.utils import create_random_plugin
from tests.users.utils import CreatedUser
from tests.utils.utils import build_random_model


def create_random_source(
    db: Session,
    parent: Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Source:
    if not isinstance(parent, Plugin):
        parent = create_random_plugin(db, parent)
    source = build_random_model(Source, plugin_id=parent.id, deleted_at=None, **kwargs)
    db.add(source)
    db.flush()  # Allows source.plugin and source.shows to be accessed.
    return source
