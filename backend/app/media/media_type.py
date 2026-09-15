# TODO: Validate

from enum import StrEnum


# TODO: Validate
class TMDBMediaType(StrEnum):
    """One of the two halves of the TMDB catalogue."""

    movie = "movie"
    tv = "tv"
