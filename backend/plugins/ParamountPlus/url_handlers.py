# TODO: Validate
"""Paramount+ URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.ParamountPlus import ParamountPlus

_SHOW_SLUG_REGEX = r"[a-z0-9-]+"
_MOVIE_ID_REGEX = r"[A-Za-z0-9]+"


# TODO: Validate
class ParamountPlusURLHandler(MediaTypeURLHandler["ParamountPlus"]):
    """What every Paramount+ URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: ParamountPlus, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key


# TODO: Validate
class ShowURLHandler(ParamountPlusURLHandler):
    """Paramount+ series URL handler.

    Example URL https://www.paramountplus.com/shows/south-park/
    """

    media_type = "series"
    _URL_REGEX = rf"\/shows\/(?P<show_id>{_SHOW_SLUG_REGEX})(?:\/|$)"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.show_page_file(self._key),
            self.url,
        )


# TODO: Validate
class MovieURLHandler(ParamountPlusURLHandler):
    """Paramount+ movie URL handler.

    Example URL https://www.paramountplus.com/movies/video/ALVE01KT235XQDEK58R7H2012VNZMK/
    """

    media_type = "movie"
    _URL_REGEX = rf"\/movies\/video\/(?P<movie_id>{_MOVIE_ID_REGEX})(?:\/|$)"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.movie_file(self._key),
            self.url,
        )
