# TODO: Validate
from datetime import UTC, datetime

from plugins.Amazon import Amazon
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)


# TODO: Validate
class AmazonValidator(PluginValidator[Amazon]):
    plugin_class = Amazon


# TODO: Validate
class TestPrimeSeries(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 11, tzinfo=UTC)
    title_key = "B0H8N888NW"
    urls = (
        "/gp/video/detail/{title_key}",
        "/dp/{title_key}",
        "https://www.amazon.com/gp/video/detail/{title_key}"
        "?jic=64%7CCgxsdW5hc3RhbmRhcmQKDHNob3V0ZmFjdG9yeRIMc3Vic2NyaXB0aW9uEgRzdm9k"
        "&ref_=atv_tv_hom_c_8zC58H_awns_5_1",
    )


# TODO: Validate
class TestMovie(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 17, tzinfo=UTC)
    title_key = "0T4FBS1H845HDEYTKZGP4Y4GTQ"
    urls = (
        "/detail/{title_key}",
        "https://www.primevideo.com/detail/{title_key}?_ssoLoop=1",
    )


# TODO: Validate
class TestDeletedMovie(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 18, tzinfo=UTC)
    title_key = "B07X35M73T"
    urls = ("/gp/video/detail/{title_key}",)


# TODO: Validate
class TestDeletedSeason(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 18, tzinfo=UTC)
    title_key = "0FKBFKZS1VKKD0L8H8CMEEQWC4"
    urls = (
        "/detail/{title_key}",
        "https://www.primevideo.com/detail/{title_key}?ref_=atv_dp_season_select_s1",
    )


# TODO: Validate
class TestMovieCollection(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 18, tzinfo=UTC)
    title_key = "B003QSLW0K"
    urls = ("https://www.amazon.com/gp/video/detail/{title_key}",)


# TODO: Validate
class TestSeriesollection(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 18, tzinfo=UTC)
    title_key = "B09ML1QV1S"
    urls = ("https://www.amazon.com/gp/video/detail/{title_key}",)


# TODO: Validate
class TestDeletedSeries(StandardTests[Amazon], AmazonValidator):
    import_time = datetime(2026, 9, 18, tzinfo=UTC)
    title_key = "0TVN8DVKCYBGQSSIDNFSE525A6"
    urls = ("https://www.primevideo.com/detail/{title_key}",)


# TODO: Validate
class TestFreeMovie(StandardTests[Amazon], AmazonValidator):
    """Test a movie that is free on Amazon.

    This is not the same as a movie that is included with Prime."""

    import_time = datetime(2026, 9, 18, tzinfo=UTC)

    title_key = "0K04DMLEJSTE354379LLPZ9ZAN"
    urls = ("https://www.primevideo.com/detail/{title_key}",)


# TODO: Validate
class TestMixedSeasonAvailibility(StandardTests[Amazon], AmazonValidator):
    """Test a season that has mixed source availability."""
    import_time = datetime(2026, 9, 18, tzinfo=UTC)
    title_key = "B0D24SZSHG"
    urls = ("https://www.amazon.com/gp/video/detail/{title_key}",)
