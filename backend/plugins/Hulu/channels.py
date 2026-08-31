# TODO: Validate
"""The plugin owned channels every Hulu title is queued into."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger

from app.channels.service import add_urls_to_channel_import_queue
from app.users.service import get_or_create_plugin_user
from plugins.Hulu.base import HuluBase
from plugins.Hulu.utils import HuluMediaType
from plugins.utils.base_plugin_v2.workers import PluginWorker

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence


# TODO: Validate
class HuluChannels(PluginWorker, HuluBase):
    """The channels Hulu's whole catalogue is read into."""

    # TODO: Validate
    def run(self, genre_ids: Collection[str] | None = None) -> None:
        """Queue every title Hulu lists, genre by genre, into its channels.

        Hulu files its catalogue under a genre at a time and nowhere else, so
        the genre pages together are the catalogue and each one is a channel of
        its own. The three channels across all of them are filled from the same
        pass rather than from a second read of every page.

        `genre_ids` narrows the run to the genres it names, which is what reads
        one genre again without the other ninety behind it.
        """
        genres_page = self.genres_page_file()
        genres_page.download_if_outdated()

        everything: list[str] = []
        movies: list[str] = []
        series: list[str] = []
        for genre_name, genre_href in genres_page.listed_items():
            genre_id = genre_href.rsplit("/", 1)[-1]
            if genre_ids is not None and genre_id not in genre_ids:
                continue
            genre_page = self.genre_page_file(genre_id)
            genre_page.download_if_outdated()
            urls = genre_page.media_urls()
            if not urls:
                logger.info("No titles listed under genre: {}", genre_id)
                continue

            logger.info("Queueing {} titles from genre: {}", len(urls), genre_id)
            self._queue(f"Hulu {genre_name}", f"All {genre_name} on Hulu.", urls)
            everything += urls
            movies += [url for url in urls if f"/{HuluMediaType.MOVIE}/" in url]
            series += [url for url in urls if f"/{HuluMediaType.SERIES}/" in url]

        self._queue("Hulu All Media", "All Media on Hulu.", everything)
        self._queue("Hulu Movies", "All Movies on Hulu.", movies)
        self._queue("Hulu TV Series", "All TV Series on Hulu.", series)

    # TODO: Validate
    def _queue(self, name: str, description: str, urls: Sequence[str]) -> None:
        if not urls:
            return
        plugin_user = get_or_create_plugin_user(session=self.session)
        channel = self.get_or_create_channel(plugin_user, name, description)
        add_urls_to_channel_import_queue(self.session, channel, urls)
