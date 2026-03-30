import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.shows.utils import create_random_show
from tests.users.utils import CreatedUser
from tests.utils.utils import build_random_model


def create_random_season(
    db: Session,
    parent: Show | Source | Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Season:
    if not isinstance(parent, Show):
        parent = create_random_show(db, parent)
    season = build_random_model(Season, show_id=parent.id, deleted_at=None, **kwargs)
    db.add(season)
    db.flush()  # Allows season.show and season.episodes to be accessed.
    return season
