# TODO: Validate
from plugins.Crunchyroll import Crunchyroll
from tests.old_mess.plugins.plugin_validator import PluginValidator, URLTests


# TODO: Validate
class CrunchyrollValidator(PluginValidator[Crunchyroll]):
    plugin_class = Crunchyroll
    urls = (
        "/series/{parse_url_response}",
        "/series/{parse_url_response}/",
        # Crunchyroll redirects a series to the URL carrying its slug, so a
        # pasted link usually carries one.
        "/series/{parse_url_response}/{show_slug}",
        # A locale sits in front of the path for anybody not browsing from the
        # default one, and the same series is behind every one of them.
        "/de/series/{parse_url_response}/{show_slug}",
    )


# A series Crunchyroll files under one listing that TMDB numbers as more than
# one title: the three seasons are a series, the movie is a film of its own, and
# the spinoff is a third. Each of them is a title the listing is a copy of.
# TODO: Validate
class TestMixedTMDB(URLTests[Crunchyroll], CrunchyrollValidator):
    parse_url_response = "GRWEW95KR"
    show_slug = "laid-back-camp"
