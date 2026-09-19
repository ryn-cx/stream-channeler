# TODO: Validate
# What the day a movie came out is written after in the tags of its hero.
RELEASE_DATE_PREFIX = "Original Premiere: "

# https://www.hidive.com/series/1286
SERIES_URL_REGEX = r"\/series\/(?P<title_key>\d+)(?:[\/?#]|$)"
# https://www.hidive.com/season/20022
SEASON_URL_REGEX = r"\/season\/(?P<season_key>\d+)(?:[\/?#]|$)"
# A season page names the series it belongs to, such as in
# https://www.hidive.com/season/36178?seriesId=4083, and the series is what the
# URL is read as because a season is too easy to land on by accident.
SEASON_SERIES_URL_REGEX = (
    r"\/season\/\d+\?(?:[^#]*&)?seriesId=(?P<title_key>\d+)(?:[&#]|$)"
)
# https://www.hidive.com/video/586784
MOVIE_URL_REGEX = r"\/video\/(?P<title_key>\d+)(?:[\/?#]|$)"

# TODO: Add support for individual episodes of a series.
