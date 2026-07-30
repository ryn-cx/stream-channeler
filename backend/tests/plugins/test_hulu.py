# TODO: Validate
from typing import override

from app.shows.models import Show
from plugins.Hulu import Hulu
from tests.plugins.plugin_validator import (
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


class HuluValidator(PluginValidator[Hulu]):
    plugin_class = Hulu
    urls: tuple[str, ...] = (
        "/series/{parse_url_response}",
        "/series/{parse_url_response}/",
    )

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


class HuluMovieValidator(PluginValidator[Hulu]):
    plugin_class = Hulu
    urls: tuple[str, ...] = (
        "/movie/{parse_url_response}",
        "/movie/{parse_url_response}/",
    )


class HuluStandardTests(StandardTests[Hulu], HuluValidator):
    pass


class HuluMovieStandardTests(StandardTests[Hulu], HuluMovieValidator):
    pass


class TestAiringShow(HuluStandardTests):
    """Tests automatically setting the next update_at value for a season"""

    parse_url_response = "4e0f6374-fc81-4da2-b7a9-f7f8c29e7acc"
    urls = (
        "/series/{parse_url_response}",
        "/series/{parse_url_response}/",
        "/series/rick-and-morty-{parse_url_response}",
    )
    search_query = "Rick and Morty"
    search_url = "https://www.hulu.com/series/4e0f6374-fc81-4da2-b7a9-f7f8c29e7acc"


class TestMovie(HuluMovieStandardTests):
    """Tests automatically setting the next update_at value for a season"""

    parse_url_response = "4ee4f57e-19bd-493f-96f9-ad3e753af981"
    urls = (
        "/movie/{parse_url_response}",
        "/movie/{parse_url_response}/",
        "/movie/the-wolf-of-wallstreet-{parse_url_response}",
    )
    search_query = "The Wolf of Wall Street"
    search_url = "https://www.hulu.com/series/4ee4f57e-19bd-493f-96f9-ad3e753af981"
