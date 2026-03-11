import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from tests.seasons.utils import create_random_season
from tests.utils.utils import build_random_model


def create_random_episode(
    db: Session,
    season: Season | None = None,
    *,
    show: Show | None = None,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> Episode:
    if season is None:
        season = create_random_season(db, show, user_id=user_id)
    episode = build_random_model(
        Episode,
        season_id=season.id,
        deleted_at=None,
        **kwargs,
    )
    db.add(episode)
    # Flush so episode.season and episode.watches can be accessed.
    db.flush()
    return episode
