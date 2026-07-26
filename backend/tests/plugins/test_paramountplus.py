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


class ParamountPlusValidator(PluginValidator[ParamountPlus]):
    plugin_class = ParamountPlus

    @override
    def update_show_validator(self, show: Show) -> Validator:
        output = super().update_show_validator(show)
        output.incremented(show.id, "update_at")
        return output


class ParamountPlusStandardTests(StandardTests[ParamountPlus], ParamountPlusValidator):
    pass


class ShowURLs:
    urls: tuple[str, ...] = (
        "/shows/{show_id}/",
        "/shows/{show_id}",
    )


class MovieURLs:
    urls: tuple[str, ...] = (
        "/movies/video/{movie_id}/",
        "/movies/video/{movie_id}",
    )


class TestSeries(ShowURLs, ParamountPlusStandardTests):
    show_id = "south-park"


class TestMovie(MovieURLs, ParamountPlusStandardTests):
    movie_id = "ALVE01KT235XQDEK58R7H2012VNZMK"


class InvalidParamountPlusValidator(InvalidURLValidator[ParamountPlus]):
    plugin_class = ParamountPlus


class TestInvalidShow(ShowURLs, InvalidParamountPlusValidator):
    show_id = "invalid-show-slug"


class TestInvalidMovie(MovieURLs, InvalidParamountPlusValidator):
    movie_id = "000000000000000000000000000000"
