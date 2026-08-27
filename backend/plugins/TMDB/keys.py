# TODO: Validate
"""What TMDB's own records are keyed by.

TMDB's records are the canonical rows themselves rather than non-canonical rows of them,
so they carry the canonical key exactly as it is written: `TMDB tv 1399`. That is what
every other plugin's non-canonical row of the title is looked up under, and a
non-canonical row is pointed at the row that key names.

A film is one record at every level, so its title, its season and its episode
are all keyed `TMDB movie 27205`. A season and an episode of a series are keyed by
their own ids rather than by their numbering, which is what the canonical rows
are keyed by; the numbering the API is asked in is read back off the files.
"""

from typing import NamedTuple

from app.canonical_media.keys import (
    EPISODE_LEVEL,
    SEASON_LEVEL,
    SHOW_LEVEL,
    parse_tmdb_key,
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_show_key,
)
from app.media.media_type import MediaType


# TODO: Validate
class RecordKey(NamedTuple):
    """The parts of a TMDB record key: which half of the catalogue, and the id."""

    media_type: MediaType
    tmdb_id: int


# TODO: Validate
def _parse(key: str, level: str) -> RecordKey:
    parsed = parse_tmdb_key(key, level)
    if parsed is None:
        message = f"{key!r} does not name a TMDB {level}"
        raise ValueError(message)
    return RecordKey(*parsed)


# TODO: Validate
def show_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the `Show` key for a title."""
    return tmdb_show_key(media_type, tmdb_id)


# TODO: Validate
def season_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the `Season` key for a season, keyed by the season's own id."""
    return tmdb_season_key(media_type, tmdb_id)


# TODO: Validate
def episode_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the `Episode` key for an episode, keyed by the episode's own id."""
    return tmdb_episode_key(media_type, tmdb_id)


# TODO: Validate
def parse_show_key(key: str) -> RecordKey:
    """Return the half of the catalogue and the id a `Show` key names."""
    return _parse(key, SHOW_LEVEL)


# TODO: Validate
def parse_season_key(key: str) -> RecordKey:
    """Return the half of the catalogue and the id a `Season` key names."""
    return _parse(key, SEASON_LEVEL)


# TODO: Validate
def parse_episode_key(key: str) -> RecordKey:
    """Return the half of the catalogue and the id an `Episode` key names."""
    return _parse(key, EPISODE_LEVEL)
