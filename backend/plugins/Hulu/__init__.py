from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
)
from plugins.Hulu.linker import HuluLinker
from plugins.Hulu.movie_importer import HuluMovieImporter
from plugins.Hulu.series_importer import HuluSeriesImporter
from plugins.Hulu.shared import HuluImporter, HuluShared
from plugins.Hulu.updater import HuluUpdater
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.catalog_support import CatalogSupport

if TYPE_CHECKING:
    from collections.abc import Collection

    from app.titles.models import Title


# TODO: Validate
class Hulu(
    HuluShared,
    BaseMediaImporterMixin,
    BasePlugin,
    register=True,
):
    CATALOG_SUPPORT = CatalogSupport.yes

    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[HuluUpdater]:
        return HuluUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[HuluLinker]:
        return HuluLinker

    # TODO: Validate
    def _hulu_updater(self) -> HuluUpdater:
        return HuluUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._hulu_updater().similar_title_urls(title)

    @override
    def _media_importer_from_url(self, url: str) -> HuluImporter:
        domain_regex = self._domains_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # Movies and series use the same URL format for individual episodes. Only a
            # series episode is served by the episode endpoint, so a movie is what is
            # left when that endpoint has nothing for the key.
            episode_file = self.episode_file(match.group("episode_key"))
            episode_file.download_if_outdated()
            if episode_file.record_content:
                return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)

        # Should only occur on invalid episode URLs.
        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> HuluImporter:
        if not title.media_type:  #  Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == MediaType.movie:
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)
        return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
