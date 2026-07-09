# TODO: Validate
from plugins.Netflix import Netflix
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)


class NetflixValidator(PluginValidator[Netflix]):
    plugin_class = Netflix


class NetflixStandardTests(StandardTests[Netflix], NetflixValidator):
    pass


class TestShow(NetflixStandardTests):
    # Virgin River — a stable public title.
    parse_url_response = "80240027"
    urls = (
        "/title/{parse_url_response}",
        "/title/{parse_url_response}/",
    )


class InvalidNetflixURLValidator(InvalidURLValidator[Netflix]):
    plugin_class = Netflix


class TestInvalidURL(InvalidNetflixURLValidator):
    # Not a title URL, so the regex rejects it.
    urls = ("https://www.netflix.com/browse",)
