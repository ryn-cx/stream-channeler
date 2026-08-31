# TODO: Validate
"""The plugin owned channels every Hulu title is queued into."""

from __future__ import annotations

from typing import TYPE_CHECKING

from loguru import logger
from sqlmodel import select

from app.channels.models import Channel
from app.channels.service import add_urls_to_channel_import_queue
from app.models import Visibility
from app.users.service import get_or_create_plugin_user
from plugins.Hulu.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.Hulu.files import FileMixin

if TYPE_CHECKING:
    from collections.abc import Collection, Sequence

    from wholoo.genre.models import GenreModel
    from wholoo.genres.models import GenresModel


# TODO: Validate
def _listed_items(page: GenresModel | GenreModel) -> list[tuple[str, str]]:
    """Return the name and address of everything a sitemap page lists.

    A page carries its own navigation and footer beside the list it is for, and
    only the list is a `list_card`, so that is what is read and the rest is left.
    """
    layout = page.props.page_props.layout
    return [
        (item.name, item.href)
        for component in layout.components or []
        if component.type == "list_card"
        for item in component.items or []
        if item.name and item.href
    ]


# TODO: Validate
class ChannelMixin(FileMixin, register=False):
    """The channels Hulu's whole catalogue is read into."""

    # TODO: Validate
    def initialize_channel(self, genre_ids: Collection[str] | None = None) -> None:
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
        for genre_name, genre_href in _listed_items(genres_page.parsed()):
            genre_id = genre_href.rsplit("/", 1)[-1]
            if genre_ids is not None and genre_id not in genre_ids:
                continue
            genre_page = self.genre_page_file(genre_id)
            genre_page.download_if_outdated()
            urls = self._title_urls(genre_page.parsed())
            if not urls:
                logger.info("No titles listed under genre: {}", genre_id)
                continue

            logger.info("Queueing {} titles from genre: {}", len(urls), genre_id)
            self._queue(f"Hulu {genre_name}", f"All {genre_name} on Hulu.", urls)
            everything += urls
            movies += [url for url in urls if f"/{MOVIE_MEDIA_TYPE}/" in url]
            series += [url for url in urls if f"/{SERIES_MEDIA_TYPE}/" in url]

        self._queue("Hulu All Media", "All Media on Hulu.", everything)
        self._queue("Hulu Movies", "All Movies on Hulu.", movies)
        self._queue("Hulu TV Series", "All TV Series on Hulu.", series)

    # TODO: Validate
    @classmethod
    def _title_urls(cls, page: GenreModel) -> list[str]:
        """Return the address of every title one genre lists, without repeats."""
        paths = {
            href: None
            for _name, href in _listed_items(page)
            if href.startswith((f"/{MOVIE_MEDIA_TYPE}/", f"/{SERIES_MEDIA_TYPE}/"))
        }
        return [cls.build_url(path) for path in paths]

    # TODO: Validate
    def _queue(self, name: str, description: str, urls: Sequence[str]) -> None:
        if not urls:
            return
        add_urls_to_channel_import_queue(
            self.session,
            self._channel(name, description),
            urls,
        )

    # TODO: Validate
    def _channel(self, name: str, description: str) -> Channel:
        """Return the plugin owned channel `name`, creating it the first time."""
        plugin_user = get_or_create_plugin_user(session=self.session)
        channel = self.session.exec(
            select(Channel)
            .where(Channel.user_id == plugin_user.id)
            .where(Channel.name == name),
        ).first()
        if channel:
            return channel

        channel = Channel(
            name=name,
            description=description,
            visibility=Visibility.public,
            anonymous=False,
            user_id=plugin_user.id,
        )
        self.session.add(channel)
        self.session.commit()
        return channel
