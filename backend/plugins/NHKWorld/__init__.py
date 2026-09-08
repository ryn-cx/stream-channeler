# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from plugins.NHKWorld.constants import TITLE_URL_REGEX
from plugins.NHKWorld.importer import NHKWorldImporter
from plugins.NHKWorld.shared import NHKWorldShared
from plugins.NHKWorld.utils import build_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from datetime import datetime

    from app.sources.models import Source
    from app.titles.models import Title


# TODO: Validate
class NHKWorldInitializer(BasePluginInitializer, NHKWorldShared):
    # TODO: Validate
    @override
    def _create_channel_records(self) -> None:
        self._feed_channel()
        self._process_new_episodes_files(self._sources[self.plugin_name()])


# TODO: Validate
class NHKWorld(NHKWorldShared, BaseReadURL, AbstractPlugin, register=False):
    initializer = NHKWorldInitializer

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TITLE_URL_REGEX,)

    # TODO: Validate
    @override
    def _validate_url(self, url: str) -> None:
        if not re.match(self._domain_regex() + TITLE_URL_REGEX, url):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> NHKWorldImporter:
        return NHKWorldImporter(self)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> NHKWorldImporter:
        return NHKWorldImporter(self)

    # TODO: Validate
    @override
    def update_source(self, source: Source, update_at: datetime) -> None:
        if source.data_timestamp is None:
            msg = "Cannot update source without a data timestamp."
            raise ValueError(msg)
        new_feed_file = self.new_video_episodes_file(source.data_timestamp)
        new_feed_file.download_if_outdated(update_at)
        self._process_new_episodes_files(source)
        self.upsert_source(source.key)

    # TODO: Validate
    @override
    def search_for_title_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.titles_search_file(names[0], 0)
        search_file.download_if_outdated()
        hits = search_file.parsed().hits.hits
        return build_url(hits[0].field_source.url) if hits else None
