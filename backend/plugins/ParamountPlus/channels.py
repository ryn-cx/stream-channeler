# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from sqlmodel import col, select

from app.channels.models import ChannelQueue, ChannelTitle
from plugins.ParamountPlus.base_files import ParamountPlusBaseFiles
from plugins.ParamountPlus.constants import MOVIE_URL_REGEX, TITLE_URL_REGEX
from plugins.ParamountPlus.files import carousel_entries
from plugins.ParamountPlus.utils import movie_url, title_url

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.channels.models import Channel
    from plugins.ParamountPlus.files import CarouselFile


# TODO: Validate
class ParamountPlusChannels(ParamountPlusBaseFiles):
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
