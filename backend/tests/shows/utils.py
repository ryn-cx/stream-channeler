import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.shows.models import Show
from tests.sources.utils import create_random_source
from tests.utils.utils import build_random_model


def create_random_show(
    db: Session,
    *,
    plugin: Plugin | None = None,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> Show:
    source = create_random_source(db, plugin, user_id=user_id)
    show = build_random_model(Show, source_id=source.id, deleted_at=None, **kwargs)
    db.add(show)
    # Flush so show.source and show.seasons can be accessed.
    db.flush()
    return show
