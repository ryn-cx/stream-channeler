import uuid

from sqlmodel import Session

from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from tests.shows.utils import create_random_show
from tests.utils.utils import build_random_model


def create_random_season(
    db: Session,
    show: Show | None = None,
    user_id: uuid.UUID | None = None,
) -> Season:
    if show is None:
        show = create_random_show(db, user_id=user_id)
    season = build_random_model(SeasonInput).upsert(show, None)
    db.commit()
    return season
