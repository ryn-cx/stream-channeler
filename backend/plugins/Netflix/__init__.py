from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Netflix.constants import TITLE_URL_REGEX
from plugins.Netflix.linker import NetflixLinker
from plugins.Netflix.movie_importer import NetflixMovieImporter
from plugins.Netflix.series_importer import NetflixSeriesImporter
from plugins.Netflix.shared import NetflixImporter, NetflixShared
from plugins.Netflix.updater import NetflixUpdater
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class Netflix(NetflixShared, BaseMediaImporterMixin, BasePlugin, register=True):
    CATALOG_SUPPORT = CatalogSupport.mostly

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[NetflixUpdater]:
        return NetflixUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[NetflixLinker]:
        return NetflixLinker

    # TODO: Validate
    def _netflix_updater(self) -> NetflixUpdater:
        return NetflixUpdater(self.session, self.plugin, self._file_cache)

    @override
    def _media_importer_from_url(self, url: str) -> NetflixImporter:
        # Movies and series use the same URL format and the same title_file, but the
        # title_file contains the media type information.
        if not (match := re.match(self._domains_regex() + TITLE_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        title_file = self.title_file(match.group("title_key"))
        self.raise_invalid_url_if_no_content(title_file, url)
        if title_file.parsed().field__typename == "Movie":
            return NetflixMovieImporter(self.session, self.plugin, self._file_cache)
        return NetflixSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._netflix_updater().similar_title_urls(title)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> NetflixImporter:
        if not title.media_type:  # Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == MediaType.movie:
            return NetflixMovieImporter(self.session, self.plugin, self._file_cache)
        return NetflixSeriesImporter(self.session, self.plugin, self._file_cache)
