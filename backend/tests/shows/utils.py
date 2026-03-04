import uuid

from sqlmodel import Session

from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from tests.sources.utils import create_random_source
from tests.utils.utils import build_random_model


def create_random_show(
    db: Session,
    source: Source | None = None,
    user_id: uuid.UUID | None = None,
) -> Show:
    if source is None:
        source = create_random_source(db, user_id=user_id)
    show = build_random_model(ShowInput).upsert(source, None)
    db.commit()
    return show
