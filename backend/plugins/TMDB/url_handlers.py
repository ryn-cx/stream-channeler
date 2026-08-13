# TODO: Validate
"""TMDB URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, override

from app.media.media_type import MediaType
from plugins.TMDB.keys import show_key
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.TMDB import TMDB


def _url_regex(media_type: MediaType) -> str:
    return rf"\/{media_type}\/(?P<{media_type}_tmdb_id>\d+)"


# TODO: Validate
class TMDBURLHandler(URLHandler["TMDB"]):
    """Base URL handler for the TMDB plugin.

    TMDB numbers films and series separately and gives each half of its
    catalogue a path of its own, so which half a URL points at is read off the
    path rather than looked up.
    """

    media_type: ClassVar[MediaType]

    # TODO: Validate
    @override
    def __init__(self, plugin: TMDB, url: str, key: str) -> None:
        self.tmdb_id = int(key)
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return show_key(self.media_type, self.tmdb_id)

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.title_page_file(self.media_type, self.tmdb_id),
            self.url,
        )


class MovieURLHandler(TMDBURLHandler):
    """TMDB movie URL handler."""

    _URL_REGEX = _url_regex(MediaType.movie)
    media_type = MediaType.movie

    @override
    def raise_if_invalid(self) -> None:
        super().raise_if_invalid()
        movie_detail_file = self.plugin.movie_detail_file(self.tmdb_id)
        self.plugin.raise_if_invalid_file(movie_detail_file, self.url)


class TvURLHandler(TMDBURLHandler):
    """TMDB TV series URL handler."""

    _URL_REGEX = _url_regex(MediaType.tv)
    media_type = MediaType.tv

    @override
    def raise_if_invalid(self) -> None:
        super().raise_if_invalid()
        show_detail_file = self.plugin.show_detail_file(self.tmdb_id)
        self.plugin.raise_if_invalid_file(show_detail_file, self.url)
