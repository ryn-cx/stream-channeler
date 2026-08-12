# TODO: Validate
"""What a canonical row's `key` says, and how to read it back.

A canonical row is named by one namespaced string rather than by columns of its
own. "YouTube dQw4w9WgXcQ" is a video only YouTube knows about; "TMDB tv show
1399" is a record TMDB holds. The first word says who issued the key, so no two
sources can collide on one.

TMDB's own keys carry two more things. The half of the catalogue comes first,
because TMDB numbers films and series separately and an id means nothing without
it. The level comes next, because a film is filed as a title, a season and an
episode all carrying the same number, and only the level tells the three apart.

Everything that used to read a `tmdb_id` column reads it back out of here, so
the key is the single thing a row's identity is stored in.
"""

from sqlalchemy import ColumnElement, or_

from app.media.media_type import MediaType

TMDB_KEY_PREFIX = "TMDB"
TMDB_KEY_LIKE = f"{TMDB_KEY_PREFIX} %"

SHOW_LEVEL = "show"
SEASON_LEVEL = "season"
EPISODE_LEVEL = "episode"

# `TMDB <media_type> <level> <tmdb_id>`, which is every part of what names a
# TMDB record and nothing else.
_TMDB_KEY_PARTS = 4


# TODO: Validate
def _tmdb_key(media_type: MediaType, level: str, tmdb_id: int) -> str:
    return f"{TMDB_KEY_PREFIX} {media_type} {level} {tmdb_id}"


# TODO: Validate
def tmdb_show_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the key naming the title TMDB holds under `tmdb_id`."""
    return _tmdb_key(media_type, SHOW_LEVEL, tmdb_id)


# TODO: Validate
def tmdb_season_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the key naming the season TMDB holds under `tmdb_id`."""
    return _tmdb_key(media_type, SEASON_LEVEL, tmdb_id)


# TODO: Validate
def tmdb_episode_key(media_type: MediaType, tmdb_id: int) -> str:
    """Return the key naming the episode TMDB holds under `tmdb_id`."""
    return _tmdb_key(media_type, EPISODE_LEVEL, tmdb_id)


# TODO: Validate
def parse_tmdb_key(key: str | None, level: str) -> tuple[MediaType, int] | None:
    """Return the half of the catalogue and the id `key` names, at `level`.

    `None` for anything that is not a TMDB key of that level, which is every key
    a website issued and every row nothing has claimed yet.
    """
    if not key:
        return None
    parts = key.split(" ")
    if len(parts) != _TMDB_KEY_PARTS:
        return None
    prefix, media_type, key_level, tmdb_id = parts
    if prefix != TMDB_KEY_PREFIX or key_level != level:
        return None
    if media_type not in MediaType.__members__ or not tmdb_id.isdigit():
        return None
    return MediaType(media_type), int(tmdb_id)


# TODO: Validate
def tmdb_id_of(key: str | None, level: str) -> int | None:
    """Return the TMDB id `key` names at `level`, if it names one."""
    parsed = parse_tmdb_key(key, level)
    return parsed[1] if parsed else None


# TODO: Validate
def tmdb_media_type_of(key: str | None, level: str) -> MediaType | None:
    """Return the half of the TMDB catalogue `key` names at `level`."""
    parsed = parse_tmdb_key(key, level)
    return parsed[0] if parsed else None


# TODO: Validate
def is_tmdb_key(key: str | None) -> bool:
    """Return whether `key` names a record TMDB holds.

    The level is not checked, since a canonical table only ever holds rows of
    its own level.
    """
    return bool(key) and key.startswith(f"{TMDB_KEY_PREFIX} ")


# TODO: Validate
def tmdb_key_clause(key_column: ColumnElement[str | None]) -> ColumnElement[bool]:
    """Return the filter matching the rows TMDB holds."""
    return key_column.like(TMDB_KEY_LIKE)


# TODO: Validate
def not_tmdb_key_clause(key_column: ColumnElement[str | None]) -> ColumnElement[bool]:
    """Return the filter matching the rows TMDB has no record of.

    A row nothing has claimed has no key at all, and it is one of them, so the
    `NULL` is spelled out rather than left to drop out of the comparison.
    """
    return or_(key_column.is_(None), key_column.not_like(TMDB_KEY_LIKE))
