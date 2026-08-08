# TODO: Validate
"""Whether TMDB holds a title as a film or as a series.

TMDB splits its catalogue in two and numbers the halves separately, so the media
type travels with the id everywhere the id goes: in keys, in identifiers, and in
the endpoints a title's files are downloaded from. Kept in one place so the
plugins and the app agree on what the two halves are called, and free of
dependencies so either side can import it.
"""

from enum import StrEnum


class MediaType(StrEnum):
    """One of the two halves of the TMDB catalogue."""

    movie = "movie"
    tv = "tv"
