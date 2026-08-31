# TODO: Validate
"""The records Hulu is given before anything is imported into it."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from loguru import logger

from app.channels.service import add_urls_to_channel_import_queue
from app.users.service import get_or_create_plugin_user
from plugins.Hulu.base import HuluBase
from plugins.Hulu.utils import HuluMediaType
from plugins.utils.base_plugin_v2.initialize import PluginInitializer

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.users.models import User


# TODO: Validate
class HuluInitializer(PluginInitializer, HuluBase):
    # TODO: Validate
    @override
    def initialize_channels(self) -> None:
        plugin_user = get_or_create_plugin_user(session=self.session)
        genres_page = self.genres_page_file()
        genres_page.download_if_outdated()

        everything: list[str] = []
        movies: list[str] = []
        series: list[str] = []
        for genre_name, genre_href in genres_page.listed_items():
            genre_id = genre_href.rsplit("/", 1)[-1]
            genre_page = self.genre_page_file(genre_id)
            genre_page.download_if_outdated()
            media_urls = genre_page.media_urls()
            logger.info("Queueing {} titles from genre: {}", len(media_urls), genre_id)
            self.initialize_channel(
                plugin_user,
                f"Hulu {genre_name}",
                f"All {genre_name} on Hulu.",
                media_urls,
            )

            everything += media_urls
            movies += [url for url in media_urls if f"/{HuluMediaType.MOVIE}/" in url]
            series += [url for url in media_urls if f"/{HuluMediaType.SERIES}/" in url]

        self.initialize_channel(
            plugin_user,
            "Hulu All Media",
            "All Media on Hulu.",
            everything,
        )
        self.initialize_channel(
            plugin_user,
            "Hulu Movies",
            "All Movies on Hulu.",
            movies,
        )
        self.initialize_channel(
            plugin_user,
            "Hulu TV Series",
            "All TV Series on Hulu.",
            series,
        )

    # TODO: Validate
    def initialize_channel(
        self,
        plugin_user: User,
        name: str,
        description: str,
        urls: Sequence[str],
    ) -> None:
        channel = self.get_or_create_channel(plugin_user, name, description)
        add_urls_to_channel_import_queue(self.session, channel, urls)
