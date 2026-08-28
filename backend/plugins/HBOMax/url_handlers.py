# TODO: Validate
"""HBO Max URL handlers."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.HBOMax.constants import SLUG_REGEX, UUID_REGEX
from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.HBOMax import HBOMax


# TODO: Validate
class HBOMaxURLHandler(MediaTypeURLHandler["HBOMax"]):
    """What every HBO Max URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: HBOMax, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key


# TODO: Validate
class ShowURLHandler(HBOMaxURLHandler):
    """HBO Max series URL handler.

    Example URL https://play.hbomax.com/show/ab553cdc-e15d-4597-b65f-bec9201fd2dd
    """

    media_type = "series"
    # Any non-movie media-type prefix maps to a series, such as mini-series in
    # https://play.hbomax.com/mini-series/396999a6-3fff-4af3-802b-10c46d10deff
    # or shows in
    # https://www.hbomax.com/shows/rick-and-morty/s2/ab553cdc-e15d-4597-b65f-bec9201fd2dd
    # The media-type path segment is any of them, e.g. show, shows, mini-series,
    # limited-series.
    _URL_REGEX = rf"\/[a-z-]+\/{SLUG_REGEX}(?:s\d+\/)?(?P<show_id>{UUID_REGEX})"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.show_file(self._key),
            self.url,
        )


# TODO: Validate
class MovieURLHandler(HBOMaxURLHandler):
    """HBO Max movie URL handler.

    Example URL https://play.hbomax.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981
    """

    media_type = "movie"
    # The title slug HBO Max puts in front of the id is decorative, such as in
    # https://www.hbomax.com/movies/the-batman/4ee4f57e-19bd-493f-96f9-ad3e753af981
    _URL_REGEX = rf"\/movies?\/{SLUG_REGEX}(?P<movie_id>{UUID_REGEX})"

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.movie_file(self._key),
            self.url,
        )
