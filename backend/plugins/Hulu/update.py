# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from loguru import logger

from plugins.Hulu.upsert import UpsertMixin
from plugins.Hulu.utils import HuluMediaType

if TYPE_CHECKING:
    from datetime import datetime

    from app.sources.models import Source


# TODO: Validate
class UpdateMixin(UpsertMixin):
    def update_source(self, source: Source, update_at: datetime) -> None:
        self.add_media_to_plugin_channels(update_at)
        self.upsert_source(source.key)

    # TODO: Validate
    def add_media_to_plugin_channels(self, update_at: datetime | None = None) -> None:
        self.genres_page_file().download_if_outdated(update_at)
        self._download_outdated_files(self._source_files(), update_at)

        all_urls: list[str] = []
        movie_urls: list[str] = []
        series_urls: list[str] = []
        for genre_name, genre_href in self.genres_page_file().listed_items():
            genre_id = genre_href.rsplit("/", 1)[-1]
            genre_urls = self.genre_page_file(genre_id).media_urls()

            self.get_or_create_channel(
                f"Hulu {genre_name}",
                f"All {genre_name} on Hulu.",
                genre_urls,
            )
            all_urls += genre_urls
            movie_urls += [url for url in genre_urls if f"/{HuluMediaType.MOVIE}/" in url]
            series_urls += [url for url in genre_urls if f"/{HuluMediaType.SERIES}/" in url]

        self.get_or_create_channel("Hulu All Media", "All Media on Hulu.", all_urls)
        self.get_or_create_channel("Hulu Movies", "All Movies on Hulu.", movie_urls)
        self.get_or_create_channel(
            "Hulu TV Series",
            "All TV Series on Hulu.",
            series_urls,
        )
