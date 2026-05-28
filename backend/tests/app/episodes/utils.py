# TODO: Validate
import uuid

from sqlmodel import Session

from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.app.seasons.utils import create_random_season
from tests.app.users.utils import CreatedUser
from tests.app.utils.utils import build_random_model


def create_random_episode(
    session: Session,
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
        parent = create_random_season(session, parent)
    episode = build_random_model(
        Episode,
        season_id=parent.id,
        deleted_at=None,
        **kwargs,
    )
    session.add(episode)
    session.flush()  # Allows episode.season and episode.watches to be accessed.
    return episode
