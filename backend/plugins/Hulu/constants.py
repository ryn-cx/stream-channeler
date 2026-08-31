# TODO: Validate
from datetime import timedelta
from enum import StrEnum


# TODO: Validate
class HuluMediaType(StrEnum):
    MOVIE = "movie"
    SERIES = "series"


DETAIL_MAX_AGE = timedelta(days=7)

UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SLUG_REGEX = r"(?:[a-z0-9-]+-)?"
