# TODO: Validate
"""TMDB's own keys carry one word more, and it is the run of numbers the id was
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

from typing import Any

from pydantic import BaseModel, ValidationError
from sqlalchemy import ColumnElement

from app.media.media_type import TMDBMediaType

TMDB_KEY_PREFIX = "TMDB"
TMDB_KEY_LIKE = f"{TMDB_KEY_PREFIX} %"

TITLE_LEVEL = "title"
SEASON_LEVEL = "season"
EPISODE_LEVEL = "episode"

# The word naming the run of numbers a record's id came from, for each level and
# half of the catalogue. A film's number is a film's at every level, since a film
# is one record however many rows stand for it.
_MOVIE_WORD = "movie"
_KEY_WORDS: dict[str, dict[TMDBMediaType, str]] = {
    TITLE_LEVEL: {TMDBMediaType.movie: _MOVIE_WORD, TMDBMediaType.tv: "tv"},
    SEASON_LEVEL: {TMDBMediaType.movie: _MOVIE_WORD, TMDBMediaType.tv: SEASON_LEVEL},
    EPISODE_LEVEL: {TMDBMediaType.movie: _MOVIE_WORD, TMDBMediaType.tv: EPISODE_LEVEL},
}


TMDB_PAGE_URL = "https://www.themoviedb.org"


# TODO: Validate
def _tmdb_key(media_type: TMDBMediaType, level: str, tmdb_id: int) -> str:
    return f"{TMDB_KEY_PREFIX} {_KEY_WORDS[level][media_type]} {tmdb_id}"


# TODO: Validate
def tmdb_title_key(media_type: TMDBMediaType, tmdb_id: int) -> str:
    """Return the unique key for a TMDB title."""
    return _tmdb_key(media_type, TITLE_LEVEL, tmdb_id)


# TODO: Validate
def tmdb_season_key(media_type: TMDBMediaType, tmdb_id: int) -> str:
    """Return the unique key for a TMDB season."""
    return _tmdb_key(media_type, SEASON_LEVEL, tmdb_id)


# TODO: Validate
def tmdb_episode_key(media_type: TMDBMediaType, tmdb_id: int) -> str:
    """Return the unique key for a TMDB episode."""
    return _tmdb_key(media_type, EPISODE_LEVEL, tmdb_id)


# TODO: Validate
def parse_tmdb_key(key: str) -> tuple[TMDBMediaType, int]:
    word, tmdb_id = key.split(" ")[1:]
    media_type = TMDBMediaType.movie if word == _MOVIE_WORD else TMDBMediaType.tv
    return media_type, int(tmdb_id)


# TODO: Validate
def get_tmdb_id(key: str) -> int:
    return parse_tmdb_key(key)[1]


# TODO: Validate
def is_tmdb_key(key: str | None) -> bool:
    return bool(key) and key.startswith(f"{TMDB_KEY_PREFIX} ")


# TODO: Validate
def tmdb_key_clause(key_column: ColumnElement[str | None]) -> ColumnElement[bool]:
    return key_column.like(TMDB_KEY_LIKE)


# TODO: Validate
def not_tmdb_key_clause(key_column: ColumnElement[str]) -> ColumnElement[bool]:
    """Return the filter matching the rows TMDB has no record of."""
    return key_column.not_like(TMDB_KEY_LIKE)


# TODO: Validate
def tmdb_episode_url(
    title_key: str | None,
    season_number: int | None,
    episode_number: int | None,
) -> str | None:
    """Return the page for an episode on themoviedb.org, if TMDB has one.

    Built from the key of the title the episode is under, which is where the
    half of the catalogue and the id both come from. A film is a single page
    with nothing below it, so its one episode is that page. Media TMDB has no
    record of has no page at all.
    """
    if not title_key or not is_tmdb_key(title_key):
        return None
    media_type, tmdb_id = parse_tmdb_key(title_key)
    if media_type is TMDBMediaType.movie:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    if season_number is None or episode_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return (
        f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
        f"/season/{season_number}/episode/{episode_number}"
    )


# TODO: Validate
def tmdb_season_url(title_key: str | None, season_number: int | None) -> str | None:
    """Return the page for a season on themoviedb.org, if TMDB has one.

    A film is a single page with nothing below it, so its one season is that
    page, and so is a series season TMDB has no number for.
    """
    if not title_key or not is_tmdb_key(title_key):
        return None
    media_type, tmdb_id = parse_tmdb_key(title_key)
    if media_type is TMDBMediaType.movie or season_number is None:
        return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}/season/{season_number}"


# TODO: Validate
def tmdb_title_url(title_key: str | None) -> str | None:
    """Return the page for a title on themoviedb.org, if TMDB has one."""
    if not title_key or not is_tmdb_key(title_key):
        return None
    media_type, tmdb_id = parse_tmdb_key(title_key)
    return f"{TMDB_PAGE_URL}/{media_type}/{tmdb_id}"


# TODO: Validate
class TmdbTitleExtra(BaseModel):
    tmdb_episode_group_id: str | None = None


# TODO: Validate
class TmdbEpisodeExtra(BaseModel):
    tmdb_season_number: int | None = None
    tmdb_episode_number: int | None = None


# TODO: Validate
def parse_episode_extra(extra: dict[str, Any] | None) -> TmdbEpisodeExtra:
    if not extra:
        return TmdbEpisodeExtra()
    try:
        return TmdbEpisodeExtra.model_validate(extra)
    except ValidationError:
        return TmdbEpisodeExtra()


# TODO: Validate
def dump_episode_extra(
    tmdb_season_number: int | None,
    tmdb_episode_number: int | None,
) -> dict[str, Any]:
    return TmdbEpisodeExtra(
        tmdb_season_number=tmdb_season_number,
        tmdb_episode_number=tmdb_episode_number,
    ).model_dump()


# TODO: Validate
def parse_extra(extra: dict[str, Any] | None) -> TmdbTitleExtra:
    """Return what `extra` says, or an empty answer where it says nothing.

    Anything that is not of this shape is read as saying nothing rather than
    raising, since `extra` is shared with whatever else a plugin keeps there and
    a row written before this existed is a row to be read, not a failure.
    """
    if not extra:
        return TmdbTitleExtra()
    try:
        return TmdbTitleExtra.model_validate(extra)
    except ValidationError:
        return TmdbTitleExtra()


# TODO: Validate
def chosen_group_id(extra: dict[str, Any] | None) -> str | None:
    """Return the episode order a title is read in, where one was chosen."""
    return parse_extra(extra).tmdb_episode_group_id


# TODO: Validate
def dump_extra(group_id: str | None) -> dict[str, Any]:
    """Return what to store in `extra` for a title read in `group_id`'s order.

    An empty object rather than one naming nothing, so a title put back to TMDB's
    own order is stored the way a title that was never moved off it is.
    """
    if not group_id:
        return {}
    return TmdbTitleExtra(tmdb_episode_group_id=group_id).model_dump()


# TODO: Validate
def get_media_type_and_tmdb_id(tmdb_title_key: str) -> tuple[TMDBMediaType, int]:
    """Return the media type and the TMDB id from an `Title.key`."""
    # Input will be either "TMDB tv ###" or "TMDB movie ###".
    return parse_tmdb_key(tmdb_title_key)


# TODO: Validate
def get_media_type_and_season_id(tmdb_season_id: str) -> tuple[TMDBMediaType, int]:
    """Return the media type and the TMDB id from an `Episode.key`."""
    # Input will be either "TMDB season ###" or "TMDB movie ###".
    return parse_tmdb_key(tmdb_season_id)


# TODO: Validate
def get_media_type_and_episode_id(tmdb_episode_key: str) -> tuple[TMDBMediaType, int]:
    """Return the media type and the TMDB id from an `Episode.key`."""
    # Input will be either "TMDB episode ###" or "TMDB movie ###".
    return parse_tmdb_key(tmdb_episode_key)


# TODO: Validate
def get_media_type(tmdb_key: str) -> TMDBMediaType:
    return parse_tmdb_key(tmdb_key)[0]


# TODO: Validate
def get_title_id(tmdb_title_key: str) -> int:
    return get_media_type_and_tmdb_id(tmdb_title_key)[1]


# TODO: Validate
def get_season_id(tmdb_season_key: str) -> int:
    return get_media_type_and_season_id(tmdb_season_key)[1]


# TODO: Validate
def get_episode_id(tmdb_episode_key: str) -> int:
    return get_media_type_and_episode_id(tmdb_episode_key)[1]
