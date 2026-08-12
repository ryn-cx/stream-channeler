# TODO: Validate
from plugins.YouTube import YouTube
from tests.old_mess.plugins.plugin_validator import StandardTests
from tests.old_mess.plugins.youtube.validators import (
    InvalidYouTubeURLValidator,
    YouTubeValidator,
)


# TODO: Validate
class TestShow(StandardTests[YouTube], YouTubeValidator):
    """Test importing a YouTube show."""

    show_key = "SCYT6SmwXZxUksg_rJd_nzuw"
    urls = ("youtube.com/show/{show_key}",)
    parse_url_response = ("show_key", show_key)


# TODO: Validate
class TestShowSeason(StandardTests[YouTube], YouTubeValidator):
    """Test importing a single season of a show.

    Only the season the URL names is whitelisted, but every season is still
    imported so the show is complete.
    """

    show_key = "SCcxGQ4YKyH9nQoeu3yH0pwg"
    season_number = "2"
    sbp = (
        "CgIyMxpJEhhVQzc2RVRYS1lab2lQV2lHNlRMeGtCTEEiLWNuY2w6OWViLTY0ODAwOGRmLT"
        "AwMDAtMjMxYy04YjYzLWY0ZjVlODA2NGM5OA%253D%253D"
    )
    urls = (
        "youtube.com/show/{show_key}?season={season_number}",
        "youtube.com/show/{show_key}?season={season_number}&sbp={sbp}",
    )
    parse_url_response = ("show_key", show_key)


# TODO: Validate
class TestInvalidShow(InvalidYouTubeURLValidator):
    urls = ("youtube.com/show/SC0123456789ABCDEFGHIJHI",)
