# TODO: Validate
import uuid

from sqlmodel import Session

from app.plugins.models import Plugin
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.users.models import User
from tests.app.helpers.utils import build_random_model
from tests.app.titles.utils import create_random_title
from tests.app.users.utils import CreatedUser


# TODO: Validate
def create_random_season(
    session: Session,
    parent: Title | Source | Plugin | User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Season:
    if not isinstance(parent, Title):
        parent = create_random_title(session, parent)
    season = build_random_model(Season, title_id=parent.id, deleted_at=None, **kwargs)
    session.add(season)
    session.flush()  # Allows season.title and season.episodes to be accessed.
    return season
