# TODO: Validate
from datetime import timedelta

MOVIE_MEDIA_TYPE = "Movie"
"""What the plugin calls a title that is a film rather than a series."""

SERIES_MEDIA_TYPE = "Series"
"""What the plugin calls a title that is a series rather than a film."""

# What the day a movie came out is written after in the tags of its hero.
RELEASE_DATE_PREFIX = "Original Premiere: "

DETAIL_MAX_AGE = timedelta(days=7)
