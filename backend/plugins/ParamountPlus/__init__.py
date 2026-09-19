from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.ParamountPlus.constants import MOVIE_URL_REGEX
from plugins.ParamountPlus.movie_importer import ParamountPlusMovieImporter
from plugins.ParamountPlus.series_importer import ParamountPlusSeriesImporter
from plugins.ParamountPlus.shared import ParamountPlusImporter, ParamountPlusShared
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime

    from app.sources.models import Source
    from app.titles.models import Title


# TODO: Validate
class ParamountPlus(ParamountPlusShared, AbstractPlugin, register=True):
    VIDEO_STORE_SCORE = False
    VIDEO_STORE_POPULARITY = False

    @override
    def _media_importer_from_url(self, url: str) -> ParamountPlusImporter:
        if re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _next_source_update_at(self) -> datetime:
        return self._staggered_monthly_update_at(
            self.source_name(),
            self._source_files_data_timestamp(),
        )

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        self._download_if_outdated(self._source_files(), update_at)
        self.create_initial_channel_records()
        self.upsert_source(source.key)

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        return self._media_importer_from_title(title).similar_title_urls(title)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> ParamountPlusImporter:
        if not title.media_type:  # Should be impossible
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == MediaType.movie:
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)
