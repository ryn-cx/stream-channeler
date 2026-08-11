# TODO: Validate
from typing import override

from app.shows.models import Show
from plugins.ParamountPlus import ParamountPlus
from tests.plugins.plugin_validator import (
    InvalidURLValidator,
    PluginValidator,
    StandardTests,
)
from tests.plugins.plugin_validator.validator import Validator


# TODO: Validate
class ParamountPlusValidator(PluginValidator[ParamountPlus]):
    plugin_class = ParamountPlus

    # TODO: Validate
    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


# TODO: Validate
class ParamountPlusStandardTests(StandardTests[ParamountPlus], ParamountPlusValidator):
    pass


# TODO: Validate
class ShowURLs:
    urls: tuple[str, ...] = (
        "/shows/{show_id}/",
        "/shows/{show_id}",
    )


# TODO: Validate
class MovieURLs:
    urls: tuple[str, ...] = (
        "/movies/video/{movie_id}/",
        "/movies/video/{movie_id}",
    )


# TODO: Validate
class TestSeries(ShowURLs, ParamountPlusStandardTests):
    show_id = "south-park"


# TODO: Validate
class TestMovie(MovieURLs, ParamountPlusStandardTests):
    movie_id = "ALVE01KT235XQDEK58R7H2012VNZMK"


# TODO: Validate
class InvalidParamountPlusValidator(InvalidURLValidator[ParamountPlus]):
    plugin_class = ParamountPlus


# TODO: Validate
class TestInvalidShow(ShowURLs, InvalidParamountPlusValidator):
    show_id = "invalid-show-slug"


# TODO: Validate
class TestInvalidMovie(MovieURLs, InvalidParamountPlusValidator):
    movie_id = "000000000000000000000000000000"
