# TODO: Validate
from plugins.TMDB import TMDB
from tests.old_mess.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    SearchTests,
    URLTests,
)


# TODO: Validate
class TMDBValidator(PluginValidator[TMDB]):
    plugin_class = TMDB
    urls = (
        "/{media_type}/{parse_url_response}",
        "/{media_type}/{parse_url_response}/",
        "/{media_type}/{parse_url_response}?language=en-US",
        # TMDB redirects a title's slug to the canonical URL, so a pasted link
        # usually carries one.
        "/{media_type}/{parse_url_response}-{show_slug}",
    )


# Not StandardTests: an import is handed off to JustWatch, so every show that
# comes back is stored under the plugin of the service it streams on. TMDB owns
# no show of its own for the update and deletion tests to work on.
# TODO: Validate
class TestShow(URLTests[TMDB], SearchTests[TMDB], TMDBValidator):
    media_type = "tv"
    parse_url_response = "85937"
    show_slug = "demon-slayer-kimetsu-no-yaiba"
    search_query = "Demon Slayer"


# TODO: Validate
class TestCrunchyrollShow(URLTests[TMDB], SearchTests[TMDB], TMDBValidator):
    media_type = "tv"
    parse_url_response = "64196"
    show_slug = "overlord"
    search_query = "Overlord"


# TODO: Validate
class TestNoJustWatch(URLTests[TMDB], TMDBValidator):
    media_type = "movie"
    parse_url_response = "1368337"
    show_slug = "the-odyssey"


# TODO: Validate
class TestTemp(URLTests[TMDB], TMDBValidator):
    urls = ("https://www.themoviedb.org/tv/209867/watch?language=en-US",)


# TODO: Validate
class InvalidTMDBURLValidator(InvalidURLValidator[TMDB]):
    plugin_class = TMDB
    urls = ("/{media_type}/{parse_url_response}",)


# TODO: Validate
class TestInvalidTitleId(InvalidTMDBURLValidator):
    # Correctly formatted show URL whose title does not exist.
    media_type = "tv"
    parse_url_response = "99999999"


# TODO: Validate
class TestInvalidURL(InvalidTMDBURLValidator):
    # A person is not importable, so the regex rejects the URL.
    media_type = "person"
    parse_url_response = "1223786"
