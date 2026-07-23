from typing import override

from app.shows.models import Show
from plugins.HBOMax import HBOMax
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class HBOMaxValidator(PluginValidator[HBOMax]):
    plugin_class = HBOMax

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


class HBOMaxStandardTests(StandardTests[HBOMax], HBOMaxValidator):
    pass


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


class MovieURLs:
    urls: tuple[str, ...] = (
        "/movie/{movie_id}",
        "/movie/{movie_id}/",
        "/movies/{slug}/{movie_id}",
        "/movies/{slug}/{movie_id}/",
    )


class TestAiringShow(ShowURLs, HBOMaxStandardTests):
    show_id = "ab553cdc-e15d-4597-b65f-bec9201fd2dd"
    slug = "rick-and-morty"


class TestMovie(MovieURLs, HBOMaxStandardTests):
    movie_id = "396999a6-3fff-4af3-802b-10c46d10deff"
    slug = "chernobyl"


class InvalidHBOMaxValidator(InvalidURLValidator[HBOMax]):
    plugin_class = HBOMax


class TestInvalidShow(ShowURLs, InvalidHBOMaxValidator):
    show_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    slug = "invalid"


class TestInvalidMovie(MovieURLs, InvalidHBOMaxValidator):
    movie_id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    slug = "invalid"
