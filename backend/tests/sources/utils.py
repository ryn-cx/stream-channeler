import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.sources.models import Source
from app.sources.schemas import SourceInput
from tests.plugins.utils import create_random_plugin
from tests.utils.utils import build_random_model


def create_random_source(
    db: Session,
    plugin: Plugin | None = None,
    user_id: uuid.UUID | None = None,
) -> Source:
    if plugin is None:
        plugin = create_random_plugin(db, user_id)
    source = build_random_model(SourceInput).upsert(plugin, None)
    db.commit()
    return source
