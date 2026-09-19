# TODO: Validate
"""What the plugin, its importers and its initializer all read Paramount+ by."""

from __future__ import annotations

import re
from abc import ABC
from typing import TYPE_CHECKING, Any, override

from sqlmodel import col, select

from app.channels.models import ChannelQueue, ChannelTitle
from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.files import (
    CarouselFile,
    CollectionFile,
    CollectionsFile,
    EpisodesFile,
    MovieFile,
    SectionFile,
    TitlePage,
    carousel_entries,
)
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from collections.abc import Sequence

    from trivial_minus.collection.models import Carousel as CollectionCarousel
    from trivial_minus.collections.models import Carousel as CollectionsCarousel
    from trivial_minus.show.models import ShowModel

    from app.channels.models import Channel
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://paramountplus.com/{path.lstrip('/')}"


# TODO: Validate
def title_url(title_key: str) -> str:
    return build_url(f"shows/{title_key}/")


# TODO: Validate
def movie_url(movie_key: str) -> str:
    return build_url(f"movies/video/{movie_key}/")


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(season_key: str) -> tuple[str, int]:
    title_key, _, season_number = season_key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def related_urls(show: ShowModel) -> list[str]:
    urls: dict[str, None] = {}
    for recommendation in show.recommendations:
        if match := re.match(MOVIE_URL_REGEX, recommendation.url):
            urls[movie_url(match.group("title_key"))] = None
        elif (match := re.match(TITLE_URL_REGEX, recommendation.url)) and (
            match.group("title_key") != "video"
        ):
            urls[title_url(match.group("title_key"))] = None
    return list(urls)


# TODO: Validate
class ParamountPlusShared(BasePlugin):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Paramount+"

    # TODO: Validate
    @classmethod
    @override
    def name_on_tmdb(cls) -> tuple[str, ...]:
        return (
            "Paramount Plus",
            "Paramount+",
            "Paramount+ Amazon Channel",
            "Paramount Plus Essential",
            "Paramount Plus Premium",
        )

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.paramountplus.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "paramountplus.com"

    # TODO: Validate
    def title_page_file(self, title_id: str) -> TitlePage:
        return self._cached_file(TitlePage, title_id)

    # TODO: Validate
    def episodes_file(
        self,
        title_id: str,
        season_number: int,
    ) -> EpisodesFile:
        return self._cached_file(EpisodesFile, title_id, season_number)

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
    def _source_files(self) -> Sequence[BaseFile[Any]]:
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
    def section_file(self, title_id: str, section_id: int) -> SectionFile:
        return self._cached_file(SectionFile, title_id, section_id)

    # TODO: Validate
    def movie_file(self, movie_id: str) -> MovieFile:
        return self._cached_file(MovieFile, movie_id)

    # TODO: Validate
    @override
    def create_initial_channel_records(self) -> None:
        for channel_key, urls in self._channel_urls().items():
            self.add_new_urls_to_channel(channel_key, urls)
            self._remove_unlisted_titles(channel_key, urls)

    # TODO: Validate
    def _channel_urls(self) -> dict[str, list[str]]:
        urls_by_channel_key: dict[str, dict[str, None]] = {}
        for collection_key, collection_name in self.collections().items():
            for carousel in self.collection_file(collection_key).parsed().carousels:
                urls = self._carousel_title_urls(self.carousel_file(carousel))
                if not urls:
                    continue
                for channel_key in (collection_name, carousel.title):
                    if channel_key:
                        urls_by_channel_key.setdefault(channel_key, {}).update(
                            dict.fromkeys(urls),
                        )
        return {
            channel_key: list(urls) for channel_key, urls in urls_by_channel_key.items()
        }

    # TODO: Validate
    def _carousel_title_urls(self, carousel_file: CarouselFile) -> list[str]:
        urls: dict[str, None] = {}
        for page in carousel_file.parsed():
            for entry in carousel_entries(page):
                if match := re.match(MOVIE_URL_REGEX, entry.href):
                    urls[movie_url(match.group("title_key"))] = None
                elif (match := re.match(TITLE_URL_REGEX, entry.href)) and (
                    match.group("title_key") != "video"
                ):
                    urls[title_url(match.group("title_key"))] = None
        return list(urls)

    # TODO: Validate
    def _remove_unlisted_titles(self, channel_key: str, urls: Sequence[str]) -> None:
        channel = self.get_or_create_channel(
            self._channel_name(channel_key),
            self._channel_description(channel_key),
        )
        listed_tmdb_title_ids = {
            tmdb_title_id
            for titles in self._titles_by_url(set(urls)).values()
            for tmdb_title_id in self._tmdb_title_ids(titles)
        }
        for channel_title in self.session.exec(
            select(ChannelTitle).where(ChannelTitle.channel_id == channel.id),
        ).all():
            if channel_title.tmdb_title_id not in listed_tmdb_title_ids:
                self.session.delete(channel_title)

        self._remove_unlisted_queue_entries(channel, urls)

    # TODO: Validate
    def _remove_unlisted_queue_entries(
        self,
        channel: Channel,
        urls: Sequence[str],
    ) -> None:
        for queue_entry in self.session.exec(
            select(ChannelQueue).where(
                ChannelQueue.channel_id == channel.id,
                col(ChannelQueue.url).not_in(urls),
            ),
        ).all():
            self.session.delete(queue_entry)


# TODO: Validate
class ParamountPlusImporter(ParamountPlusShared, BaseImporter, ABC):
    pass
