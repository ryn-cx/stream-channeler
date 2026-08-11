# TODO: Validate
"""TMDB URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar, override

from app.media.media_type import MediaType
from plugins.TMDB.keys import show_key
from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.TMDB import TMDB
    from plugins.TMDB.files import TitlePage
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
def _title_url_regex(media_type: MediaType) -> str:
    """Return the regex for the page of a title of `media_type`.

    Nothing after the id is matched. TMDB redirects a bare title URL to one
    carrying the title's slug, and a link can point at a sub-page of the title
    such as `/watch`, but the id is what names the title in every one of them.

    The group is named after the media type because every handler's regex is
    joined into one alternation to match a URL against the plugin, and a name
    used twice in a pattern is an error.
    """
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
        # The page and the API are separate enough that TMDB can serve one for a
        # title and not the other, and both are read, so a URL is only valid once
        # each of them has answered for it.
        self.plugin.raise_if_invalid_file(self.title_page_file(), self.url)
        self.plugin.raise_if_invalid_file(self.detail_file(), self.url)

    # TODO: Validate
    def title_page_file(self) -> TitlePage:
        """Return the themoviedb.org page for the title the URL names."""
        return self.plugin.title_page_file(self.media_type, self.tmdb_id)

    # TODO: Validate
    def detail_file(self) -> BaseFile[Any]:
        """Return the file the title's own media is imported from."""
        return self.plugin._show_files(self.show_key)[0]  # noqa: SLF001 - Same plugin.


# TODO: Validate
class MovieURLHandler(TMDBURLHandler):
    """TMDB movie URL handler.

    Supported URL Formats:
        - https://www.themoviedb.org/movie/1368337
        - https://www.themoviedb.org/movie/1368337-the-odyssey
    """

    _URL_REGEX = _title_url_regex(MediaType.movie)
    media_type = MediaType.movie


# TODO: Validate
class TvURLHandler(TMDBURLHandler):
    """TMDB TV series URL handler.

    Supported URL Formats:
        - https://www.themoviedb.org/tv/85937
        - https://www.themoviedb.org/tv/85937-demon-slayer-kimetsu-no-yaiba
        - https://www.themoviedb.org/tv/209867/watch?language=en-US
    """

    _URL_REGEX = _title_url_regex(MediaType.tv)
    media_type = MediaType.tv
