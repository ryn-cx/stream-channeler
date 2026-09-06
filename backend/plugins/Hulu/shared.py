# TODO: Validate
"""What the plugin, its importers and its initializer all read Hulu by."""

from __future__ import annotations

from typing import override

from app.sources.models import Source
from app.utils import tz_datetime
from app.utils.strict_re import strict_search
from app.utils.update_at import staggered_monthly_update_at
from plugins.Hulu.basic_files import BasicFiles
from plugins.Hulu.utils import (
    search_url,
    title_urls,
)

UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SLUG_REGEX = r"(?:[a-z0-9-]+-)?"
SERIES_URL_REGEX = rf"\/series\/{SLUG_REGEX}(?P<series_key>{UUID_REGEX})"
MOVIE_URL_REGEX = rf"\/movie\/{SLUG_REGEX}(?P<movie_key>{UUID_REGEX})"
VIDEO_URL_REGEX = rf"\/watch\/(?P<episode_key>{UUID_REGEX})"


class HuluShared(BasicFiles):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    @override
    def upsert_source(self, source_key: str) -> Source:
        file_timestamps = self._file_timestamps(self._source_files())
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            data_timestamp=file_timestamps[0],
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(
            staggered_monthly_update_at(source_key, tz_datetime.now()),
            file_timestamps,
        )
        return source

    # TODO: Validate
    def _create_channel_records(self) -> None:
        self.add_urls_to_plugin_channel(
            "Hulu - All Titles",
            "All Titles on Hulu.",
            self._all_title_urls(),
        )

    # TODO: Validate
    def _all_title_urls(self) -> list[str]:
        return [
            *title_urls(self.all_series_file().parsed()),
            *title_urls(self.all_movies_file().parsed()),
        ]

    # TODO: Validate
    def _listed_show_keys(self) -> set[str]:
        show_keys: set[str] = set()
        for url in self._all_title_urls():
            match = strict_search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url)
            show_keys.add(match.group("series_key") or match.group("movie_key"))
        return show_keys
