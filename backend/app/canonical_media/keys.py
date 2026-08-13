# TODO: Validate
"""What a canonical row's `key` says, and how to read it back.

A canonical row is named by one namespaced string rather than by columns of its
own. "YouTube dQw4w9WgXcQ" is a video only YouTube knows about; "TMDB tv 1399" is
a record TMDB holds. The first word says who issued the key, so no two sources
can collide on one.

TMDB's own keys carry one word more, and it is the run of numbers the id was
issued from. TMDB numbers four things apart from each other - films, series,
series seasons and series episodes - so a number means nothing until which of the
four it came from is said, and saying it is the whole of what the word is for:
"TMDB movie 27205", "TMDB tv 1399", "TMDB season 3624", "TMDB episode 63056".

A film is numbered once and stands as a title, a season and an episode all at
that one number, so all three of its rows are named "TMDB movie 27205". Nothing
is lost by that: a season is named within the title above it and an episode
within its season, so the three never have to be told apart from one another.

Everything that used to read a `tmdb_id` column reads it back out of here, so
the key is the single thing a row's identity is stored in.
"""

from sqlalchemy import ColumnElement, func

from app.media.media_type import MediaType

TMDB_KEY_PREFIX = "TMDB"
TMDB_KEY_LIKE = f"{TMDB_KEY_PREFIX} %"

SHOW_LEVEL = "show"
SEASON_LEVEL = "season"
EPISODE_LEVEL = "episode"

# The word naming the run of numbers a record's id came from, for each level and
# half of the catalogue. A film's number is a film's at every level, since a film
# is one record however many rows stand for it.
_MOVIE_WORD = "movie"
_KEY_WORDS: dict[str, dict[MediaType, str]] = {
    SHOW_LEVEL: {MediaType.movie: _MOVIE_WORD, MediaType.tv: "tv"},
    SEASON_LEVEL: {MediaType.movie: _MOVIE_WORD, MediaType.tv: SEASON_LEVEL},
    EPISODE_LEVEL: {MediaType.movie: _MOVIE_WORD, MediaType.tv: EPISODE_LEVEL},
}
_MEDIA_TYPES: dict[str, dict[str, MediaType]] = {
    level: {word: media_type for media_type, word in words.items()}
    for level, words in _KEY_WORDS.items()
}

# `TMDB <word> <tmdb_id>`, which is every part of what names a TMDB record and
# nothing else.
_TMDB_KEY_PARTS = 3


# TODO: Validate
def _tmdb_key(media_type: MediaType, level: str, tmdb_id: int) -> str:
    return f"{TMDB_KEY_PREFIX} {_KEY_WORDS[level][media_type]} {tmdb_id}"


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
def record_key(plugin_key: str, key: str) -> str:
    """Return the key naming what a website's own record is a copy of.

    A plugin's own key for a record already names the thing itself rather than
    one listing of it — a YouTube episode is keyed by its video id, which is the
    same id wherever that video turns up — so namespacing it by the plugin is
    enough to make two copies of one work agree on a single row.
    """
    return f"{plugin_key} {key}"


# TODO: Validate
def parse_tmdb_key(key: str | None, level: str) -> tuple[MediaType, int] | None:
    """Return the half of the catalogue and the id `key` names, at `level`.

    The word says which run of numbers the id came from, and at a given level
    only two of the four runs can name a record: a film's own numbering, and the
    series numbering of that level. So the word is what says which half of the
    catalogue the record belongs to, and a word from another level's run - a
    season's, read as though it named an episode - names nothing here.

    `None` for anything that is not a TMDB key of that level, which is every key
    a website issued.
    """
    if not key:
        return None
    parts = key.split(" ")
    if len(parts) != _TMDB_KEY_PARTS:
        return None
    prefix, word, tmdb_id = parts
    if prefix != TMDB_KEY_PREFIX or not tmdb_id.isdigit():
        return None
    media_type = _MEDIA_TYPES[level].get(word)
    if media_type is None:
        return None
    return media_type, int(tmdb_id)


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
def not_tmdb_key_clause(key_column: ColumnElement[str]) -> ColumnElement[bool]:
    """Return the filter matching the rows TMDB has no record of."""
    return key_column.not_like(TMDB_KEY_LIKE)


# TODO: Validate
def key_issuer(key_column: ColumnElement[str]) -> ColumnElement[str]:
    """Return who issued the record `key_column` names."""
    return func.split_part(key_column, " ", 1)


# TODO: Validate
def same_issuer_clause(
    first: ColumnElement[str],
    second: ColumnElement[str],
) -> ColumnElement[bool]:
    """Return the filter matching two keys that were issued by the same source.

    A title's own catalogue is the run of records whoever issued the title
    issued, so a row a website minted under a title TMDB issued is a record of
    the website's rather than one of the title's own. A website carries an
    episode the title has no record of - an extra it filed under the season, a
    film it sells as part of the series - and a canonical row is minted for it
    so the copy has something to hang off, but the title it was filed under
    still does not hold it.
    """
    return key_issuer(first) == key_issuer(second)
