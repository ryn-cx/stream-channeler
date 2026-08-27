# TODO: Validate
from datetime import timedelta

MOVIE_MEDIA_TYPE = "movie"
"""What Hulu calls a title that is a film rather than a series."""

SERIES_MEDIA_TYPE = "series"
"""What Hulu calls a title that is a series rather than a film."""

DETAIL_MAX_AGE = timedelta(days=7)

UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SLUG_REGEX = r"(?:[a-z0-9-]+-)?"
