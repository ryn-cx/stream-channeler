# TODO: Validate
from typing import override

from app.shows.models import Show
from plugins.Roku import Roku
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


# TODO: Validate
class RokuValidator(PluginValidator[Roku]):
    plugin_class = Roku

    # TODO: Validate
    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


# TODO: Validate
class RokuStandardTests(StandardTests[Roku], RokuValidator):
    pass


# TODO: Validate
class ContentURLs:
    urls: tuple[str, ...] = (
        "/details/{content_id}/{slug}",
        "/details/{content_id}/{slug}/",
        "/details/{content_id}",
        "/watch/{content_id}",
    )


# TODO: Validate
class TestMovie(ContentURLs, RokuStandardTests):
    content_id = "483059d5c8f85421ae634f5d5653dbdb"
    slug = "hellboy"


# TODO: Validate
class TestSingleSeasonShow(ContentURLs, RokuStandardTests):
    content_id = "25f0bf59c5bc50a2a8189fb835034dd0"
    slug = "mr-bean"


# TODO: Validate
class TestMultipleSeasonsShow(ContentURLs, RokuStandardTests):
    content_id = "db1607f1cff2522bb795382bb4b5bcae"
    slug = "fawlty-towers"


# TODO: Validate
class InvalidRokuValidator(InvalidURLValidator[Roku]):
    plugin_class = Roku


# TODO: Validate
class TestInvalid(ContentURLs, InvalidRokuValidator):
    content_id = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
    slug = "invalid"
