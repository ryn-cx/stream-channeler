# TODO: Validate
"""What the plugin, its importers and its initializer all read Hulu by."""

from __future__ import annotations

from typing import override

from app.sources.models import Source
from app.utils.strict_re import strict_search
from plugins.Hulu.base_files import HuluBaseFiles
from plugins.Hulu.utils import (
    HuluMediaType,
    search_url,
    title_url,
    title_urls,
)

UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
SLUG_REGEX = r"(?:[a-z0-9-]+-)?"
SERIES_URL_REGEX = rf"\/series\/{SLUG_REGEX}(?P<series_key>{UUID_REGEX})"
MOVIE_URL_REGEX = rf"\/movie\/{SLUG_REGEX}(?P<movie_key>{UUID_REGEX})"
VIDEO_URL_REGEX = rf"\/watch\/(?P<episode_key>{UUID_REGEX})"


# TODO: Validate
class HuluShared(HuluBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    # TODO: Validate
    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    def _create_channel_records(self) -> None:
        channel = self.get_or_create_channel(
            "Hulu - All Titles",
            "All Titles on Hulu.",
        )
        self.add_new_urls_to_channel(channel, self._title_urls_from_all_xxx_files())

    # TODO: Validate
    def _title_urls_from_all_xxx_files(self) -> list[str]:
        """Get all title urls from the AllMovies and AllSeries files."""
        urls = []
        for url in (
            *title_urls(self.all_series_file().parsed()),
            *title_urls(self.all_movies_file().parsed()),
        ):
            match = strict_search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url)
            if series_key := match.group("series_key"):
                urls.append(title_url(series_key, HuluMediaType.SERIES))
            else:
                urls.append(title_url(match.group("movie_key"), HuluMediaType.MOVIE))
        return urls

    # TODO: Validate
    def _title_keys_from_all_xxx_files(self) -> set[str]:
        """Get all title keys from the AllMovies and AllSeries files."""
        title_keys: set[str] = set()
        for url in self._title_urls_from_all_xxx_files():
            match = strict_search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url)
            title_keys.add(match.group("series_key") or match.group("movie_key"))
        return title_keys
