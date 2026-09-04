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

from app.canonical_media.keys import (
    EPISODE_LEVEL,
    SEASON_LEVEL,
    SHOW_LEVEL,
    parse_tmdb_key,
)
from app.media.media_type import TMDBMediaType


# TODO: Validate
def _parse(key: str, level: str) -> tuple[TMDBMediaType, int]:
    parsed = parse_tmdb_key(key, level)
    if parsed is None:
        message = f"{key!r} does not name a TMDB {level}"
        raise ValueError(message)
    return parsed


# TODO: Validate
def get_media_type_and_tmdb_id(show_key: str) -> tuple[TMDBMediaType, int]:
    """Return the half of the catalogue and the id a `Show` key names.

    `TMDB tv 1399` for a series, `TMDB movie 27205` for a film.
    """
    return _parse(show_key, SHOW_LEVEL)


# TODO: Validate
def parse_season_key(key: str) -> tuple[TMDBMediaType, int]:
    """Return the half of the catalogue and the id a `Season` key names.

    `TMDB season 3624` for a season of a series, `TMDB movie 27205` for a film.
    """
    return _parse(key, SEASON_LEVEL)


# TODO: Validate
def parse_episode_key(key: str) -> tuple[TMDBMediaType, int]:
    """Return the half of the catalogue and the id an `Episode` key names.

    `TMDB episode 63056` for an episode of a series, `TMDB movie 27205` for a film.
    """
    return _parse(key, EPISODE_LEVEL)
