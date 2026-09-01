# TODO: Validate
TMDB_DOMAIN = "themoviedb.org"


# TODO: Validate
def media_url(media_type: str, tmdb_id: int) -> str:
    """Return the TMDb URL for the movie or tv series."""
    return f"https://www.{TMDB_DOMAIN}/{media_type}/{tmdb_id}"
