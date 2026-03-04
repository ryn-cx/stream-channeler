import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.seasons.models import Season
from tests.seasons.utils import create_random_season
from tests.utils.utils import build_random_model


def create_random_episode(
    db: Session,
    season: Season | None = None,
    user_id: uuid.UUID | None = None,
) -> Episode:
    if season is None:
        season = create_random_season(db, user_id=user_id)
    episode = build_random_model(EpisodeInput).upsert(season, None)
    db.commit()
    return episode
