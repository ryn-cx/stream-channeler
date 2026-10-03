# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from app.titles.models import Title
from app.tmdb_media.tmdb import get_media_type_and_tmdb_id
from plugins.TMDB.constants import MOVIE_URL_REGEX
from plugins.TMDB.linker import TMDBLinker
from plugins.TMDB.movie_importer import TMDBMovie
from plugins.TMDB.series_importer import TMDBSeries
from plugins.TMDB.shared import TMDBImporter, TMDBPluginShared
from plugins.TMDB.updater import TMDBUpdater
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.media_importer import BaseMediaImporterMixin

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from app.plugins.schemas import (
        PluginSearchResults,
        SearchWatchProviders,
        TMDBMediaInfo,
    )
    from plugins.TMDB.updater import TMDBSearchResult
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
class TMDB(TMDBPluginShared, BaseMediaImporterMixin, BasePlugin, register=True):
    # TODO: Validate
    @classmethod
    @override
    def _plugin_updater_class(cls) -> type[TMDBUpdater]:
        return TMDBUpdater

    # TODO: Validate
    @classmethod
    @override
    def _plugin_linker_class(cls) -> type[TMDBLinker]:
        return TMDBLinker

    # TODO: Validate
    def _tmdb_updater(self) -> TMDBUpdater:
        return TMDBUpdater(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> TMDBImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return TMDBMovie(self.session, self.plugin, self._file_cache)
        return TMDBSeries(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> TMDBImporter:
        media_type, _ = get_media_type_and_tmdb_id(title.key)
        if media_type == TMDBMediaType.movie:
            return TMDBMovie(self.session, self.plugin, self._file_cache)
        return TMDBSeries(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._tmdb_updater().similar_title_urls(title)

    # TODO: Validate
    def tmdb_url_from_imdb_id(self, imdb_id: str) -> str:
        return self._tmdb_updater().tmdb_url_from_imdb_id(imdb_id)

    # TODO: Validate
    def search(
        self,
        media_type: TMDBMediaType | None,
        query: str,
        exact_year: int | None,
        rough_year: int | None,
    ) -> list[TMDBSearchResult]:
        return self._tmdb_updater().search(media_type, query, exact_year, rough_year)

    # TODO: Validate
    def import_search_result(
        self,
        search_result: TMDBSearchResult,
    ) -> list[URLImportResult]:
        return self._tmdb_updater().import_search_result(search_result)

    # TODO: Validate
    def in_app_search(
        self,
        query: str,
        cursor: str | None = None,
    ) -> PluginSearchResults:
        return self._tmdb_updater().in_app_search(query, cursor)

    # TODO: Validate
    def title_info(self, media_identifier: str) -> TMDBMediaInfo:
        return self._tmdb_updater().title_info(media_identifier)

    # TODO: Validate
    def search_watch_providers(
        self,
        media_identifiers: Sequence[str],
    ) -> SearchWatchProviders:
        return self._tmdb_updater().search_watch_providers(media_identifiers)
