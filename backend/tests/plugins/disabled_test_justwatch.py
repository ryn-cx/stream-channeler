# TODO: Validate
from plugins.JustWatch import JustWatch

from tests.plugins.plugin_validator import PluginValidator, StandardTests


# TODO: Validate
class JustWatchValidator(PluginValidator[JustWatch]):
    plugin_class = JustWatch
    urls = (
        "/{locale}/{media_type}/{title_slug}",
        "/{locale}/{media_type}/{title_slug}/",
        # The address as JustWatch serves it, which is what a pasted link is.
        "https://www.justwatch.com/{locale}/{media_type}/{title_slug}",
        # A title reached from a listing carries where it was reached from, and
        # the page is the same title without it.
        "/{locale}/{media_type}/{title_slug}?ref=search",
        "/{locale}/{media_type}/{title_slug}#offers",
    )


# A title carried by services this project has no scraper of its own for, which
# is what JustWatch is kept for: those listings are stored out of what JustWatch
# says about them, since nothing else here has an account of them.
# TODO: Validate
class TestTVShow1(StandardTests[JustWatch], JustWatchValidator):
    """JustWatch has a long-running series carried by several services."""

    locale = "us"
    media_type = "tv-title"
    title_slug = "family-guy"
