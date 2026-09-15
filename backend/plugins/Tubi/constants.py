# TODO: Validate
CONTENT_ID_REGEX = r"\d+"
# Every title path ends with an optional slug, e.g. /megamind or /season-1.
SLUG_REGEX = r"(?:\/[^\/?#]*)?"

# https://tubitv.com/movies/100029837/megamind
MOVIE_URL_REGEX = rf"\/movies\/(?P<title_key>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
# https://tubitv.com/series/300006854/scooby-doo-where-are-you
SERIES_URL_REGEX = rf"\/series\/(?P<title_key>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
# https://tubitv.com/tv-shows/595036/s01-e01-what-a-night-for-a-knight
EPISODE_URL_REGEX = (
    rf"\/tv-shows\/(?P<episode_key>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
)
