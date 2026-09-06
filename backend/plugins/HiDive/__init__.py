# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HiDive.media import HiDiveMedia, HiDiveMovie, HiDiveSeries
from plugins.HiDive.shared import (
    MOVIE_URL_REGEX,
    SEASON_URL_REGEX,
    SERIES_URL_REGEX,
    HiDiveShared,
)
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer
from plugins.utils.base_plugin.search import BaseCatalogueSearchMixin

if TYPE_CHECKING:
    from datetime import datetime

    from app.sources.models import Source
    from app.titles.models import Title


# TODO: Validate
class HiDiveInitializer(BasePluginInitializer, HiDiveShared):
    # TODO: Validate
    @override
    def _create_channel_records(self) -> None:
        self._schedule_channel()
        self._process_new_schedule_files(self._sources[self.plugin_name()])


# TODO: Validate
class HiDive(
    HiDiveShared,
    BaseCatalogueSearchMixin,
    BaseReadURL,
    AbstractPlugin,
    register=False,
):
    initializer = HiDiveInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, SEASON_URL_REGEX, MOVIE_URL_REGEX)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Title | str) -> HiDiveMedia:
        if isinstance(input, str):
            domain_regex = self._domain_regex()
            if re.match(domain_regex + SERIES_URL_REGEX, input):
                return HiDiveSeries(self)
            if re.match(domain_regex + SEASON_URL_REGEX, input):
                return HiDiveSeries(self)
            if re.match(domain_regex + MOVIE_URL_REGEX, input):
                return HiDiveMovie(self)

            msg = f"Invalid {self.plugin_name()} URL: {input}"
            raise InvalidURLError(msg)

        if not input.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if input.media_type == "Movie":
            return HiDiveMovie(self)
        return HiDiveSeries(self)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_schedule_file = self.schedule_file(source.data_timestamp)
        new_schedule_file.download_if_outdated(update_at)
        self._process_new_schedule_files(source)
        self.upsert_source(source.key)
