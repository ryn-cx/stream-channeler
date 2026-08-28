# TODO: Validate
import uuid

from sqlmodel import Session

from app.episodes.models import Episode, EpisodeCanonicalEpisode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.app.helpers.utils import build_random_model
from tests.app.seasons.utils import create_random_season
from tests.app.users.utils import CreatedUser


# TODO: Validate
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
    kwargs.setdefault("is_canonical", True)
    episode = build_random_model(
        Episode,
        season_id=parent.id,
        deleted_at=None,
        **kwargs,
    )
    session.add(episode)
    session.flush()  # Allows episode.season and episode.watches to be accessed.
    return episode


# TODO: Validate
def create_linked_episode(
    session: Session,
    parent: Season | None = None,
    **kwargs: object,
) -> Episode:
    """Create a non-canonical `Episode` beside the canonical one it stands for.

    What a plugin reads off a website is a row standing for the episode rather
    than the episode itself, and several of the reads only find an episode
    through that link, so a test about them needs the pair rather than a single
    row standing for itself.
    """
    canonical = create_random_episode(session, parent, **kwargs)
    non_canonical = create_random_episode(
        session,
        canonical.season,
        **{**kwargs, "is_canonical": False},
    )
    session.add(
        EpisodeCanonicalEpisode(
            episode_id=non_canonical.id,
            canonical_episode_id=canonical.id,
        ),
    )
    session.flush()
    return non_canonical
