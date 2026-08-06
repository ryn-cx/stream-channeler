# TODO: Validate
from typing import override

from app.shows.models import Show
from plugins.Amazon import Amazon
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class AmazonValidator(PluginValidator[Amazon]):
    plugin_class = Amazon

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


class AmazonStandardTests(StandardTests[Amazon], AmazonValidator):
    pass


class DetailURLs:
    urls: tuple[str, ...] = (
        "/dp/{asin}",
        "/dp/{asin}?lv=shuf&channelId=500&plpRedirect=mhFallback",
        "/gp/video/detail/{asin}",
    )


class TestFreeMovie(DetailURLs, AmazonStandardTests):
    """Test a free movie on Prime Video."""

    asin = "B0GHXVBQLM"


class TestPaidMovie(DetailURLs, AmazonStandardTests):
    """Test a paid movie on Prime Video."""

    asin = "B0H3QRLYCN"


class TestPaidOrRentMovie(DetailURLs, AmazonStandardTests):
    """Test a paid or rent movie on Prime Video."""

    asin = "B0FZLW2HCF"


class TestFreeTVShow(DetailURLs, AmazonStandardTests):
    """Test a free TV show on Prime Video."""

    asin = "B09PWHKFR2"


class TestPaidTVShow(DetailURLs, AmazonStandardTests):
    """Test a paid TV show on Prime Video."""

    asin = "B09PWHKFR2"


class TestPaidOrRentTVShow(DetailURLs, AmazonStandardTests):
    """Test a paid or rent TV show on Prime Video."""

    asin = "B00C16ID14"


class TestTVShowPaginatedEpisode(DetailURLs, AmazonStandardTests):
    """Test a TV show whose episodes do not fit on one page.

    The episode list holds 24 episodes at a time, so this season's 33 episodes are
    split over two pages and the second page has to be read as well.
    """

    asin = "B005C8DB7E"
