# TODO: Validate
from plugins.JustWatch import JustWatch
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)


class JustWatchValidator(PluginValidator[JustWatch]):
    plugin_class = JustWatch


class JustWatchStandardTests(StandardTests[JustWatch], JustWatchValidator):
    pass


class MovieURLs:
    urls: tuple[str, ...] = (
        "/us/movie/{slug}",
        "/us/movie/{slug}/",
    )


class ShowURLs:
    urls: tuple[str, ...] = (
        "/us/tv-show/{slug}",
        "/us/tv-show/{slug}/",
    )


# class TestMovie(MovieURLs, JustWatchStandardTests):
#     # Megamind (2010), streaming on Tubi.
#     slug = "megamind"


# class TestSingleSeasonShow(ShowURLs, JustWatchStandardTests):
#     # Strip Law — a single season, streaming on Netflix.
#     slug = "strip-law"


class TestMixedSourceShow(ShowURLs, JustWatchStandardTests):
    slug = "the-bear"


class InvalidJustWatchValidator(InvalidURLValidator[JustWatch]):
    plugin_class = JustWatch


class TestInvalidMovie(MovieURLs, InvalidJustWatchValidator):
    slug = "invalid-movie-that-does-not-exist"


class TestInvalidShow(ShowURLs, InvalidJustWatchValidator):
    slug = "invalid-show-that-does-not-exist"
