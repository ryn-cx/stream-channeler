# TODO: Validate
"""What the plugin, its importers and its initializer all read Adult Swim by."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.AdultSwim.base_files import AdultSwimBaseFiles
from plugins.AdultSwim.constants import CLIPS, FREE, SUBSCRIPTION
from plugins.AdultSwim.utils import is_clips_source, title_url

if TYPE_CHECKING:
    from app.channels.models import Channel
    from app.sources.models import Source


# TODO: Validate
class AdultSwimShared(AdultSwimBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Adult Swim"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.adultswim.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "adultswim.com"

    # TODO: Validate
    @classmethod
    @override
    def _source_keys(cls) -> tuple[str, ...]:
        return (FREE, SUBSCRIPTION, CLIPS)

    # TODO: Validate
    @override
    def _upsert_source(self, source_key: str) -> Source:
        source = super()._upsert_source(source_key)
        if is_clips_source(source_key):
            source.link_to_tmdb = False
        return source

    # TODO: Validate
    def _create_initial_channel_records(self) -> None:
        self.add_new_urls_to_channel(
            [("All Titles", url) for url in self._title_urls_from_plugin_files()],
        )

    # TODO: Validate
    def _title_urls_from_plugin_files(self) -> list[str]:
        return [title_url(title_key) for title_key in self._title_keys_from_plugin_files()]

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        return [
            show.slug
            for show in self.titles_file().parsed().shows
            if show.slug is not None
        ]

    # TODO: Validate
    def _channel(self) -> Channel:
        return self.get_or_create_channel(
            self._channel_name("All Titles"),
            self._channel_description("All Titles"),
        )
