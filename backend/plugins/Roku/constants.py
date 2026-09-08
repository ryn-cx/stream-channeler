# TODO: Validate
MOVIE_TYPE = "movie"

# Movies, series and episodes use a plain content id, a season appends its number.
CONTENT_ID_REGEX = r"[0-9a-f]{32}(?:-\d+)?"

# https://therokuchannel.roku.com/details/db1607f1cff2522bb795382bb4b5bcae
# The title slug after the content id is decorative, only the id matters.
DETAILS_URL_REGEX = (
    rf"\/details\/(?P<details_content_key>{CONTENT_ID_REGEX})(?:\/[^\/?#]+)?(?:\/|$)"
)
# https://therokuchannel.roku.com/watch/db1607f1cff2522bb795382bb4b5bcae
WATCH_URL_REGEX = rf"\/watch\/(?P<watch_content_key>{CONTENT_ID_REGEX})(?:\/|$)"
