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


class TestSeries(DetailURLs, AmazonStandardTests):
    asin = "B095RHJ52R"


class TestPaidShow(DetailURLs, AmazonStandardTests):
    asin = "0GK0W5DZFOWP14GMAR51GE1AYD"


class InvalidAmazonValidator(InvalidURLValidator[Amazon]):
    plugin_class = Amazon


class TestInvalid(DetailURLs, InvalidAmazonValidator):
    asin = "B000000000"
