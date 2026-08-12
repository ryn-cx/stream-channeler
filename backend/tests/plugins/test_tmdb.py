# TODO: Validate
from plugins.TMDB import TMDB
from tests.old_mess.plugins.plugin_validator import PluginValidator, URLTests


# TODO: Validate
class TMDBValidator(PluginValidator[TMDB]):
    plugin_class = TMDB
    urls = (
        "/{media_type}/{parse_url_response}",
        "/{media_type}/{parse_url_response}/",
        "/{media_type}/{parse_url_response}?language=en-US",
        # A title's own sub-pages carry the id too, and the watch page is what a
        # link to where a title streams points at.
        "/{media_type}/{parse_url_response}/watch?language=en-US",
        # TMDB redirects a title's slug to the canonical URL, so a pasted link
        # usually carries one.
        "/{media_type}/{parse_url_response}-{show_slug}",
    )


# TODO: Validate
class TestMovieWithMixedCrunchyroll(URLTests[TMDB], TMDBValidator):
    media_type = "movie"
    parse_url_response = "566466"
    show_slug = "laid-back-camp-the-movie"


# TODO: Validate
class TestTVWithMixedCrunchyroll(URLTests[TMDB], TMDBValidator):
    media_type = "tv"
    parse_url_response = "76075"
    show_slug = "laid-back-camp"
    urls = (
        *TMDBValidator.urls,
        # Only a show has seasons, so the page listing them is a sub-page a
        # movie's URLs cannot carry.
        "/{media_type}/{parse_url_response}/seasons?language=en-US",
    )
