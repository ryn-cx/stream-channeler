# TODO: Validate
from app.media.media_type import TMDBMediaType


# TODO: Validate
def title_url_regex(media_type: TMDBMediaType) -> str:
    """Return the regex pattern for the given media type."""
    return rf"\/{media_type}\/(?P<title_key>\d+)"


MOVIE_URL_REGEX = title_url_regex(TMDBMediaType.movie)


TV_URL_REGEX = title_url_regex(TMDBMediaType.tv) + (
    r"(?:\/season\/(?P<season_number>\d+)(?:\/episode\/(?P<episode_number>\d+))?)?"
)
