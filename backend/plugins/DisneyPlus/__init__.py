# TODO: Validate
from __future__ import annotations

from pathlib import PurePosixPath
from typing import TYPE_CHECKING, override
from urllib.parse import parse_qs, urlsplit

from plugins.DisneyPlus.linker import DisneyPlusLinker
from plugins.DisneyPlus.movie_importer import DisneyPlusMovieImporter
from plugins.DisneyPlus.series_importer import DisneyPlusSeriesImporter
from plugins.DisneyPlus.shared import DisneyPlusImporter, DisneyPlusShared
from plugins.DisneyPlus.updater import DisneyPlusUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from app.titles.models import Title


# TODO: Validate
class DisneyPlus(
    DisneyPlusShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.mostly
    KNOWN_ISSUES = (
        "Only the first 24 episodes of each season are supported. There is a $20 "
        "bounty for anyone who fixes this and submits a pull request to "
        "[knee-minus](https://github.com/ryn-cx/knee-minus)."
    )
    PROXY_IMAGES = True

    # TODO: Validate
    @staticmethod
    @override
    def image_file_name(url: str) -> str:
        parts = urlsplit(url)
        image_id = PurePosixPath(parts.path).parent.name
        return f"{image_id}.{parse_qs(parts.query)['format'][0]}"

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[DisneyPlusUpdater]:
        return DisneyPlusUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[DisneyPlusLinker]:
        return DisneyPlusLinker

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> DisneyPlusImporter:
        title_key = self._url_title_key(url)
        entity_file = self.entity_file(title_key)
        self.raise_invalid_url_if_no_content(entity_file, url)
        if self.is_movie(entity_file.parsed()):
            return DisneyPlusMovieImporter(self.session, self.plugin, self._file_cache)
        return DisneyPlusSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> DisneyPlusImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return DisneyPlusMovieImporter(self.session, self.plugin, self._file_cache)
        return DisneyPlusSeriesImporter(self.session, self.plugin, self._file_cache)
