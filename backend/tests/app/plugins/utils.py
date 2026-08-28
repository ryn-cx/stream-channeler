# TODO: Validate
from sqlmodel import Session

from app.plugins.models import Plugin
from tests.app.helpers.utils import build_random_model


# TODO: Validate
def create_random_plugin(session: Session, **kwargs: object) -> Plugin:
    """Create a `Plugin`.

    A plugin belongs to nobody and is the same for everybody, so there is no owner
    to give it and no visibility to set on it.
    """
    plugin = build_random_model(Plugin, deleted_at=None, **kwargs)
    session.add(plugin)
    session.flush()  # Allows plugin.sources and plugin.files to be accessed.
    return plugin
