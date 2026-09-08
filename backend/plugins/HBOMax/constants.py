# TODO: Validate
UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SLUG_REGEX = r"(?:[a-z0-9-]+\/)?"

# The title slug HBO Max puts in front of the id is decorative, such as in
# https://www.hbomax.com/movies/the-batman/4ee4f57e-19bd-493f-96f9-ad3e753af981
MOVIE_URL_REGEX = rf"\/movies?\/{SLUG_REGEX}(?P<movie_key>{UUID_REGEX})"
# Any non-movie media-type prefix maps to a series, such as mini-series in
# https://play.hbomax.com/mini-series/396999a6-3fff-4af3-802b-10c46d10deff
# or shows in
# https://www.hbomax.com/shows/rick-and-morty/s2/ab553cdc-e15d-4597-b65f-bec9201fd2dd
# The media-type path segment is any of them, e.g. show, shows, mini-series,
# limited-series.
TITLE_URL_REGEX = rf"\/[a-z-]+\/{SLUG_REGEX}(?:s\d+\/)?(?P<title_key>{UUID_REGEX})"
