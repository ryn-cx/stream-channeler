# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HiDive.constants import MOVIE_URL_REGEX, SEASON_URL_REGEX, SERIES_URL_REGEX
from plugins.HiDive.importer import (
    HiDiveImporter,
    HiDiveMovieImporter,
    HiDiveSeriesImporter,
)
from plugins.HiDive.shared import HiDiveShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from datetime import datetime

    from app.sources.models import Source
    from app.titles.models import Title


# TODO: Validate
class HiDive(
    HiDiveShared,
    BaseImporter,
    AbstractPlugin,
    register=False,
):
    # TODO: Validate
    @override
    def _create_initial_channel_records(self) -> None:
        self._schedule_channel()
        self._process_new_schedule_files(self._sources[self.plugin_name()])

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, SEASON_URL_REGEX, MOVIE_URL_REGEX)

    # TODO: Validate
    @override
    def _validate_url(self, url: str) -> None:
        domain_regex = self._domains_regex()
        for url_regex in (SERIES_URL_REGEX, SEASON_URL_REGEX, MOVIE_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> HiDiveImporter:
        domain_regex = self._domains_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HiDiveSeriesImporter(self.session, self.plugin, self._file_cache)
        if re.match(domain_regex + SEASON_URL_REGEX, url):
            return HiDiveSeriesImporter(self.session, self.plugin, self._file_cache)
        return HiDiveMovieImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> HiDiveImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return HiDiveMovieImporter(self.session, self.plugin, self._file_cache)
        return HiDiveSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_schedule_file = self.schedule_file(source.data_timestamp)
        new_schedule_file.download_if_outdated(update_at)
        self._process_new_schedule_files(source)
        self._upsert_source(source.key)
