import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from tests.plugins.utils import create_random_plugin
from tests.utils.utils import build_random_model


def create_random_source(
    db: Session,
    plugin: Plugin | None = None,
    *,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> Source:
    if plugin is None:
        plugin = create_random_plugin(db, user_id=user_id)
    source = build_random_model(Source, plugin_id=plugin.id, deleted_at=None, **kwargs)
    db.add(source)
    # Flush so source.plugin and source.shows can be accessed.
    db.flush()
    return source
