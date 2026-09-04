# TODO: Validate


"""Which TMDB episode an `Episode` is linked to, and the ones it could be.

An import points an episode at TMDB by name, and an episode whose name matched
nothing is left standing only for itself. Those are what is gathered here, each
paired with the TMDB episode that came closest, so the link a name could not
make can be made by hand instead: the episodes still waiting on somebody, the
episodes of a title one of them could be, and the writing down of whichever a
`User` settles on.
"""

from sqlmodel import Session

from app.episodes.models import (
    Episode,
)
from app.episodes.schemas import (
    UserEpisodeUrlOutput,
)
from app.episodes.user_urls import (
    canonical_episode_for_url,
    clear_user_episode_url,
    set_user_episode_url,
)
from app.users.models import User


# TODO: Validate
def set_episode_url_for_user(
    session: Session,
    episode: Episode,
    current_user: User,
    url: str,
) -> UserEpisodeUrlOutput:
    """Point a `User`'s own copy of an `Episode` at a URL of their choosing."""
    canonical_episode_id = canonical_episode_for_url(episode)
    record = set_user_episode_url(session, current_user, canonical_episode_id, url)
    return UserEpisodeUrlOutput(
        canonical_episode_id=canonical_episode_id,
        url=record.url,
    )


# TODO: Validate
def clear_episode_url_for_user(
    session: Session,
    episode: Episode,
    current_user: User,
) -> UserEpisodeUrlOutput:
    """Drop the URL a `User` gave for an `Episode`."""
    canonical_episode_id = canonical_episode_for_url(episode)
    clear_user_episode_url(session, current_user, canonical_episode_id)
    return UserEpisodeUrlOutput(canonical_episode_id=canonical_episode_id, url=None)
