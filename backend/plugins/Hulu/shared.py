# TODO: Validate
"""What the plugin, its importers and its initializer all read Hulu by."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.canonical_media.service.identifiers import canonical_show_ids_by_key
from app.sources.models import Source
from app.utils import tz_datetime
from app.utils.strict_re import strict_search
from app.utils.update_at import staggered_monthly_update_at
from plugins.Hulu.basic_files import BasicFiles
from plugins.Hulu.utils import (
    HuluMediaType,
    listed_items,
    media_urls,
    search_url,
)

if TYPE_CHECKING:
    from collections.abc import Sequence
    from uuid import UUID

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
        existing_source = Source.get_from_memory(self.session, self.plugin, source_key)
        source = Source(
            key=source_key,
            name=self.plugin_name(),
            favicon_url=self.favicon_url(),
            data_timestamp=self.genres_file().data_timestamp(),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, existing_source)
        source.set_update_at(
            staggered_monthly_update_at(source_key, tz_datetime.now()),
            self._file_timestamps(self._source_files()),
        )
        return source

    def add_media_to_plugin_channels(self) -> None:
        all_urls: list[str] = []
        movie_urls: list[str] = []
        series_urls: list[str] = []
        for genre_name, genre_href in listed_items(self.genres_file().parsed()):
            genre_id = genre_href.rsplit("/", 1)[-1]
            genre_urls = media_urls(self.genre_file(genre_id).parsed())

            self._replace_plugin_channel_media(
                f"Hulu {genre_name}",
                f"All {genre_name} on Hulu.",
                genre_urls,
            )
            all_urls += genre_urls
            movie_urls += [
                url for url in genre_urls if f"/{HuluMediaType.MOVIE}/" in url
            ]
            series_urls += [
                url for url in genre_urls if f"/{HuluMediaType.SERIES}/" in url
            ]

        self._replace_plugin_channel_media(
            "Hulu All Media",
            "All Media on Hulu.",
            all_urls,
        )
        self._replace_plugin_channel_media(
            "Hulu Movies",
            "All Movies on Hulu.",
            movie_urls,
        )
        self._replace_plugin_channel_media(
            "Hulu TV Series",
            "All TV Series on Hulu.",
            series_urls,
        )

    # TODO: Validate
    def _canonical_show_ids(self, urls: Sequence[str]) -> set[UUID]:
        """Converts a list of Hulu URLs to a set of canonical show IDs."""
        show_keys: set[str] = set()
        for url in urls:
            match = strict_search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url)
            show_keys.add(match.group("series_key") or match.group("movie_key"))
        return {
            show_id
            for show_ids in canonical_show_ids_by_key(self.session, show_keys).values()
            for show_id in show_ids
        }

    def _replace_plugin_channel_media(
        self,
        channel_name: str,
        channel_description: str,
        urls: Sequence[str],
    ) -> None:
        channel = self.add_urls_to_plugin_channel(
            channel_name,
            channel_description,
            urls,
        )

        canonical_show_ids = self._canonical_show_ids(urls)
        for channel_show in list(channel.shows):
            if channel_show.canonical_show_id not in canonical_show_ids:
                self.session.delete(channel_show)
        self.session.commit()
