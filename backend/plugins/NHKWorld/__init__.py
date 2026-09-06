# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from plugins.NHKWorld.media import NHKWorldMedia
from plugins.NHKWorld.shared import SHOW_URL_REGEX, NHKWorldShared
from plugins.NHKWorld.utils import build_url
from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from datetime import datetime

    from app.shows.models import Show
    from app.sources.models import Source


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
        return (SHOW_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_importer(self, input: Show | str) -> NHKWorldMedia:
        return NHKWorldMedia(self)

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
    def search_for_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        search_file = self.shows_search_file(names[0], 0)
        search_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        hits = search_file.parsed().hits.hits
        return build_url(hits[0].field_source.url) if hits else None
