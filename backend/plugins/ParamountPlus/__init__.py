# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.ParamountPlus.media import (
    ParamountPlusMedia,
    ParamountPlusMovie,
    ParamountPlusSeries,
)
from plugins.ParamountPlus.shared import (
    MOVIE_URL_REGEX,
    TITLE_URL_REGEX,
    ParamountPlusShared,
)
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class ParamountPlusInitializer(BasePluginInitializer, ParamountPlusShared): ...


# TODO: Validate
class ParamountPlus(ParamountPlusShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = ParamountPlusInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Title | str) -> ParamountPlusMedia:
        if isinstance(input, str):
            domain_regex = self._domain_regex()
            if re.match(domain_regex + MOVIE_URL_REGEX, input):
                return ParamountPlusMovie(self)
            if re.match(domain_regex + TITLE_URL_REGEX, input):
                return ParamountPlusSeries(self)

            msg = f"Invalid {self.plugin_name()} URL: {input}"
            raise InvalidURLError(msg)

        if not input.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return ParamountPlusMovie(self)
        return ParamountPlusSeries(self)
