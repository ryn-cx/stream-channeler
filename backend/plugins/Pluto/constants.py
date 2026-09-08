# TODO: Validate
# The website serves every on-demand page under a locale segment.
LOCALE = "en"

MILLISECONDS_PER_SECOND = 1000

ITEM_ID_REGEX = r"[0-9a-f]{24}"
# Optional locale segment, e.g. /en, /us or /en-gb.
LOCALE_REGEX = r"(?:\/[a-z]{2}(?:-[a-z]{2})?)?"
# Optional suffix the website adds to the canonical URL of a title.
DETAILS_REGEX = r"(?:\/details)?"

# https://pluto.tv/en/on-demand/movies/68a54f49df1220b53566f16e/details
# https://pluto.tv/us/on-demand/movies/68a54f49df1220b53566f16e
MOVIE_URL_REGEX = (
    rf"{LOCALE_REGEX}\/on-demand\/movies\/(?P<movie_key>{ITEM_ID_REGEX})"
    rf"{DETAILS_REGEX}(?:\/|$)"
)
# https://pluto.tv/en/on-demand/series/5ef05c6acdce3c001a779a79/details
# https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1
# https://pluto.tv/us/on-demand/series/5ef05c6acdce3c001a779a79/season/1/episode/5ef05c6ecdce3c001a779a95
SERIES_URL_REGEX = (
    rf"{LOCALE_REGEX}\/on-demand\/series\/(?P<series_key>{ITEM_ID_REGEX})"
    # The optional segments of a link that points at a season or an
    # episode of a series.
    rf"(?:\/season\/\d+(?:\/episode\/(?P<episode_key>{ITEM_ID_REGEX}))?)?"
    rf"{DETAILS_REGEX}(?:\/|$)"
)
