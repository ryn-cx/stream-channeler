import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from app.users.models import User
from tests.app.plugins.utils import create_random_plugin
from tests.app.users.utils import CreatedUser
from tests.app.utils.utils import build_random_model


def create_random_source(
    session: Session,
    parent: Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Source:
    if not isinstance(parent, Plugin):
        parent = create_random_plugin(session, parent)
    source = build_random_model(Source, plugin_id=parent.id, deleted_at=None, **kwargs)
    session.add(source)
    session.flush()  # Allows source.plugin and source.shows to be accessed.
    return source
