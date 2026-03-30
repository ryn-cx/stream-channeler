import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.seasons.utils import create_random_season
from tests.users.utils import CreatedUser
from tests.utils.utils import build_random_model


def create_random_episode(
    db: Session,
    parent: Season
    | Show
    | Source
    | Plugin
    | User
    | CreatedUser
    | uuid.UUID
    | None = None,
    **kwargs: object,
) -> Episode:
    if not isinstance(parent, Season):
        parent = create_random_season(db, parent)
    episode = build_random_model(
        Episode,
        season_id=parent.id,
        deleted_at=None,
        **kwargs,
    )
    db.add(episode)
    db.flush()  # Allows episode.season and episode.watches to be accessed.
    return episode
