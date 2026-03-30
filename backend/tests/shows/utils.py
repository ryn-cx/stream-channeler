import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.sources.utils import create_random_source
from tests.users.utils import CreatedUser
from tests.utils.utils import build_random_model


def create_random_show(
    db: Session,
    parent: Source | Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Show:
    if not isinstance(parent, Source):
        parent = create_random_source(db, parent)
    show = build_random_model(Show, source_id=parent.id, deleted_at=None, **kwargs)
    db.add(show)
    db.flush()  # Allows show.source and show.seasons to be accessed.
    return show
