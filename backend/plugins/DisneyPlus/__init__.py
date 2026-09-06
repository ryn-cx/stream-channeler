# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.DisneyPlus.media import (
    DisneyPlusMedia,
    DisneyPlusMovie,
    DisneyPlusSeries,
)
from plugins.DisneyPlus.shared import ENTITY_URL_REGEX, DisneyPlusShared
from plugins.DisneyPlus.utils import is_movie
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class DisneyPlusInitializer(BasePluginInitializer, DisneyPlusShared): ...


# TODO: Validate
class DisneyPlus(DisneyPlusShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = DisneyPlusInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (ENTITY_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Title | str) -> DisneyPlusMedia:
        if isinstance(input, str):
            match = re.match(self._domain_regex() + ENTITY_URL_REGEX, input)
            if not match:
                msg = f"Invalid {self.plugin_name()} URL: {input}"
                raise InvalidURLError(msg)

            # Movies and series are answered at the same address, so the page has
            # to be read before it is known which of the two it is.
            title_key = match.group("entity_key")
            self.raise_if_invalid_file(self.entity_file(title_key), input)
            if is_movie(self.entity_file(title_key).parsed()):
                return DisneyPlusMovie(self)
            return DisneyPlusSeries(self)

        if not input.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return DisneyPlusMovie(self)
        return DisneyPlusSeries(self)
