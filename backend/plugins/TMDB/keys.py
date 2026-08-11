# TODO: Validate
from typing import NamedTuple

from app.media.media_type import MediaType

# A movie has no seasons or episodes of its own, so it is stored as a single
# season holding a single episode, both numbered zero.
MOVIE_SEASON_NUMBER = 0
MOVIE_EPISODE_NUMBER = 0


# TODO: Validate
class ShowKey(NamedTuple):
    """The parts of a TMDB `Show` key."""

    media_type: MediaType
    tmdb_id: int


# TODO: Validate
class SeasonKey(NamedTuple):
    """The parts of a TMDB `Season` key."""

    media_type: MediaType
    tmdb_id: int
    season_number: int


# TODO: Validate
class EpisodeKey(NamedTuple):
    """The parts of a TMDB `Episode` key."""

    media_type: MediaType
    tmdb_id: int
    season_number: int
    episode_number: int


# TODO: Validate
def show_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the `Show` key for a title."""
    return f"{media_type}/{tmdb_id}"


# TODO: Validate
def season_key(media_type: MediaType, tmdb_id: int, season_number: int) -> str:
    """Return the `Season` key for a season of a title."""
    return f"{media_type}/{tmdb_id}/{season_number}"


# TODO: Validate
def episode_key(
    media_type: MediaType,
    tmdb_id: int,
    season_number: int,
    episode_number: int,
) -> str:
    """Return the `Episode` key for an episode of a title."""
    return f"{media_type}/{tmdb_id}/{season_number}/{episode_number}"


# TODO: Validate
def parse_show_key(key: str) -> ShowKey:
    """Return the media type and TMDB id a `Show` key is built from."""
    media_type, tmdb_id = key.split("/")
    return ShowKey(MediaType(media_type), int(tmdb_id))


# TODO: Validate
def parse_season_key(key: str) -> SeasonKey:
    """Return the parts a `Season` key is built from.

    A season is reached from its key alone, without the show's, so the key
    carries everything the show's does as well.
    """
    media_type, tmdb_id, season_number = key.split("/")
    return SeasonKey(MediaType(media_type), int(tmdb_id), int(season_number))


# TODO: Validate
def parse_episode_key(key: str) -> EpisodeKey:
    """Return the parts an `Episode` key is built from."""
    media_type, tmdb_id, season_number, episode_number = key.split("/")
    return EpisodeKey(
        MediaType(media_type),
        int(tmdb_id),
        int(season_number),
        int(episode_number),
    )
