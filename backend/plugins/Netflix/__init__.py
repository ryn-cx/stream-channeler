# TODO: Validate
from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.importer import (
    NetflixImporter,
    NetflixMovieImporter,
    NetflixSeriesImporter,
)
from plugins.Netflix.shared import NetflixShared
from plugins.Netflix.utils import first_search_result_key, is_movie, title_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class NetflixInitializer(BasePluginInitializer, NetflixShared): ...


# TODO: Validate
class Netflix(NetflixShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = NetflixInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def media_importer_from_url(self, url: str) -> NetflixImporter:
        match = re.match(self._domain_regex() + TITLE_URL_REGEX, url)
        if not match:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        # Movies and series are answered at the same address, so the title
        # has to be read before it is known which of the two it is.
        title_key = match.group("title_key")
        self.raise_if_invalid_file(self.title_file(title_key), url)
        if is_movie(self.title_file(title_key).parsed(), title_key):
            return NetflixMovieImporter(self)
        return NetflixSeriesImporter(self)

    # TODO: Validate
    @override
    def media_importer_from_title(self, title: Title) -> NetflixImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return NetflixMovieImporter(self)
        return NetflixSeriesImporter(self)

    # TODO: Validate
    @override
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.search_file(names[0], None)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=30))
        title_key = first_search_result_key(search_file.parsed())
        if title_key is None:
            return None
        return title_url(title_key)
