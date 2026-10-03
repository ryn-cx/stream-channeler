# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, override

from app.utils import tz_datetime
from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.files import (
    CarouselFile,
    CollectionFile,
    CollectionsFile,
    carousel_entries,
)
from plugins.ParamountPlus.shared import ParamountPlusShared
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from trivial_minus.collection.models import Carousel as CollectionCarousel
    from trivial_minus.collections.models import Carousel as CollectionsCarousel

    from app.files.models import File
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class ParamountPlusUpdater(ParamountPlusShared, BasePluginUpdater):
    # TODO: Validate
    @override
    def _import_plugin_files(self) -> None:
        self.create_initial_channel_records()
        self._mark_titles_with_changed_season_counts()

    # TODO: Validate
    def _mark_titles_with_changed_season_counts(self) -> None:
        carousel_files = sorted(
            (file for file in self._plugin_files() if isinstance(file, CarouselFile)),
            key=lambda file: file.record_data_timestamp,
        )
        listings: dict[str, list[list[str | int]]] = {}
        for carousel_file in carousel_files:
            for page in carousel_file.parsed():
                for entry in carousel_entries(page):
                    match = re.match(TITLE_URL_REGEX, entry.href)
                    if (
                        match
                        and match.group("title_key") != "video"
                        and entry.content
                        and entry.content.available_video_seasons
                    ):
                        listings[match.group("title_key")] = [
                            [season.season_num, season.total_count]
                            for season in entry.content.available_video_seasons
                        ]
        self._mark_titles_with_changed_listings(
            None,
            listings,
            carousel_files[-1].record_data_timestamp,
        )

    # TODO: Validate
    def collections_file(self) -> CollectionsFile:
        return self._cached_file(CollectionsFile)

    # TODO: Validate
    def collection_file(self, collection_id: str) -> CollectionFile:
        return self._cached_file(CollectionFile, collection_id)

    # TODO: Validate
    def carousel_file(
        self,
        carousel: CollectionsCarousel | CollectionCarousel,
    ) -> CarouselFile:
        return self._cached_file(
            CarouselFile,
            carousel.slug,
            str(carousel.carousel_id),
            carousel.token,
        )

    # TODO: Validate
    def carousel_files(
        self,
        carousels: Sequence[CollectionsCarousel | CollectionCarousel],
    ) -> list[CarouselFile]:
        return [self.carousel_file(carousel) for carousel in carousels]

    # TODO: Validate
    @override
    def update_file(self, file: File) -> None:
        if file.update_at and file.update_at > tz_datetime.now():
            return
        if file.key.startswith(f"{CarouselFile.class_key()}/"):
            self.update_plugin_files()
            if not self.is_plugin_file(file):
                file.update_at = None
            return
        super().update_file(file)

    # TODO: Validate
    @override
    def _plugin_files(self) -> Sequence[BaseFile[Any]]:
        collections_file = self.collections_file()
        collections_file.download_if_outdated()
        hub_carousel_files = self.carousel_files(collections_file.parsed().carousels)
        self._download_if_outdated(hub_carousel_files)

        files: list[BaseFile[Any]] = [collections_file, *hub_carousel_files]
        for collection_key in self.collections():
            collection_file = self.collection_file(collection_key)
            collection_file.download_if_outdated()
            files.append(collection_file)
            files += self.carousel_files(collection_file.parsed().carousels)
        return files

    # TODO: Validate
    def collections(self) -> dict[str, str]:
        names: dict[str, str] = {}
        carousels = self.collections_file().parsed().carousels
        for carousel_file in self.carousel_files(carousels):
            for page in carousel_file.parsed():
                for entry in carousel_entries(page):
                    if entry.slug and entry.title:
                        names.setdefault(entry.slug, entry.title)
        return names

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        return list(
            dict.fromkeys(
                url for urls, _ in self._channel_urls().values() for url in urls
            ),
        )

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        for channel_key, (urls, data_timestamp) in self._channel_urls().items():
            self.replace_list_channels({channel_key: urls}, data_timestamp)

    # TODO: Validate
    def _channel_urls(self) -> dict[str, tuple[list[str], datetime]]:
        urls_by_channel_key: dict[str, dict[str, None]] = {}
        data_timestamps: dict[str, datetime] = {}
        for collection_key, collection_name in self.collections().items():
            collection_file = self.collection_file(collection_key)
            for carousel in collection_file.parsed().carousels:
                carousel_file = self.carousel_file(carousel)
                urls = self._carousel_title_urls(carousel_file)
                if not urls:
                    continue
                data_timestamp = min(
                    collection_file.record_data_timestamp,
                    carousel_file.record_data_timestamp,
                )
                for channel_key in (collection_name, carousel.title):
                    if channel_key:
                        urls_by_channel_key.setdefault(channel_key, {}).update(
                            dict.fromkeys(urls),
                        )
                        data_timestamps[channel_key] = min(
                            data_timestamps.get(channel_key, data_timestamp),
                            data_timestamp,
                        )
        return {
            channel_key: (list(urls), data_timestamps[channel_key])
            for channel_key, urls in urls_by_channel_key.items()
        }

    # TODO: Validate
    def _carousel_title_urls(self, carousel_file: CarouselFile) -> list[str]:
        urls: dict[str, None] = {}
        for page in carousel_file.parsed():
            for entry in carousel_entries(page):
                if match := re.match(MOVIE_URL_REGEX, entry.href):
                    urls[self.movie_url(match.group("title_key"))] = None
                elif (match := re.match(TITLE_URL_REGEX, entry.href)) and (
                    match.group("title_key") != "video"
                ):
                    urls[self.title_url(match.group("title_key"))] = None
        return list(urls)
