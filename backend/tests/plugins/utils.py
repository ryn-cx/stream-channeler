import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.plugins.schemas import PluginInput
from tests.utils.utils import build_random_model


def create_random_plugin(db: Session, user_id: uuid.UUID | None = None) -> Plugin:
    plugin_input = build_random_model(PluginInput)
    plugin_input.user_id = user_id
    plugin = plugin_input.upsert(db, None)
    db.commit()
    return plugin
