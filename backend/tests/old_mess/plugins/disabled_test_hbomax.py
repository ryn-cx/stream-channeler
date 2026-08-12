# TODO: Validate
from typing import override

from app.shows.models import Show
from plugins.HBOMax import HBOMax
from tests.old_mess.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.old_mess.plugins.plugin_validator.validator import Validator


# TODO: Validate
class HBOMaxValidator(PluginValidator[HBOMax]):
    plugin_class = HBOMax

    # TODO: Validate
    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


# TODO: Validate
class HBOMaxStandardTests(StandardTests[HBOMax], HBOMaxValidator):
    pass


# TODO: Validate
class ShowURLs:
    urls: tuple[str, ...] = (
        "/show/{show_id}",
        "/show/{show_id}/",
        "/mini-series/{show_id}",
        "/mini-series/{show_id}/",
        "/shows/{slug}/{show_id}",
        "/shows/{slug}/{show_id}/",
        "/mini-series/{slug}/{show_id}",
        "/mini-series/{slug}/{show_id}/",
    )


# TODO: Validate
class MovieURLs:
    urls: tuple[str, ...] = (
        "/movie/{movie_id}",
        "/movie/{movie_id}/",
        "/movies/{slug}/{movie_id}",
        "/movies/{slug}/{movie_id}/",
    )


# TODO: Validate
class TestAiringShow(ShowURLs, HBOMaxStandardTests):
    show_id = "ab553cdc-e15d-4597-b65f-bec9201fd2dd"
    slug = "rick-and-morty"


# TODO: Validate
class TestMovie(MovieURLs, HBOMaxStandardTests):
    movie_id = "396999a6-3fff-4af3-802b-10c46d10deff"
    slug = "chernobyl"


# TODO: Validate
class InvalidHBOMaxValidator(InvalidURLValidator[HBOMax]):
    plugin_class = HBOMax


# TODO: Validate
class TestInvalidShow(ShowURLs, InvalidHBOMaxValidator):
    show_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    slug = "invalid"


# TODO: Validate
class TestInvalidMovie(MovieURLs, InvalidHBOMaxValidator):
    movie_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    slug = "invalid"
