from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.utils.update_at import staggered_monthly_update_at
from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.importer import (
    ParamountPlusImporter,
    ParamountPlusMovieImporter,
    ParamountPlusSeriesImporter,
)
from plugins.ParamountPlus.shared import ParamountPlusShared
from plugins.utils.abstract_plugin import AbstractPlugin

if TYPE_CHECKING:
    from datetime import datetime

    from app.sources.models import Source
    from app.titles.models import Title


class ParamountPlus(ParamountPlusShared, AbstractPlugin, register=True):
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TITLE_URL_REGEX)

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
        return staggered_monthly_update_at(
            self.source_name(),
            min(self._source_files_data_timestamps()),
        )

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        self._download_if_outdated(self._source_files(), update_at)
        self.create_initial_channel_records()
        self.upsert_source(source.key)

    @override
    def similar_title_urls(self, title: Title) -> list[str]:
        return self._media_importer_from_title(title).similar_title_urls(title)

    @override
    def _media_importer_from_title(self, title: Title) -> ParamountPlusImporter:
        if not title.media_type:  # Should be impossible
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return ParamountPlusMovieImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        return ParamountPlusSeriesImporter(self.session, self.plugin, self._file_cache)
