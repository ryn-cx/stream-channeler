# TODO: Validate
"""What every other part of the plugin reads a Watchmode title by."""

from __future__ import annotations

from wampi.extract_title_id import extract_title_id

from app.media.media_type import TMDBMediaType


# TODO: Validate
def title_key(media_type: TMDBMediaType, tmdb_id: int) -> str:
    """Return the Watchmode title id for a TMDB id."""
    if media_type == TMDBMediaType.movie:
        return extract_title_id(tmdb_movie_id=tmdb_id)
    return extract_title_id(tmdb_tv_id=tmdb_id)
