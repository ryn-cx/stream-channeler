# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.HBOMax import HBOMax

_UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_SLUG_REGEX = r"(?:[a-z0-9-]+\/)?"
_SEASON_REGEX = r"(?:s\d+\/)?"
# Any media-type path segment, e.g. show, shows, mini-series, limited-series.
_MEDIA_TYPE_REGEX = r"[a-z-]+"


class HBOMaxURLHandler(MediaTypeURLHandler["HBOMax"]):
    def __init__(self, plugin: HBOMax, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    @override
    def show_key(self) -> str:
        return self._key


class ShowURLHandler(HBOMaxURLHandler):
    media_type = "series"
    # Any non-movie media-type prefix maps to a series.
    # https://play.hbomax.com/show/ab553cdc-e15d-4597-b65f-bec9201fd2dd
    # https://play.hbomax.com/mini-series/396999a6-3fff-4af3-802b-10c46d10deff
    # https://www.hbomax.com/shows/rick-and-morty/s2/ab553cdc-e15d-4597-b65f-bec9201fd2dd
    _PATH_REGEX = rf"\/{_MEDIA_TYPE_REGEX}\/{_SLUG_REGEX}{_SEASON_REGEX}(?P<show_id>{_UUID_REGEX})"

    @override
    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.show_file(self._key),
            self.url,
        )


class MovieURLHandler(HBOMaxURLHandler):
    media_type = "movie"
    # https://play.hbomax.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981
    # https://www.hbomax.com/movies/the-batman/4ee4f57e-19bd-493f-96f9-ad3e753af981
    _PATH_REGEX = rf"\/movies?\/{_SLUG_REGEX}(?P<movie_id>{_UUID_REGEX})"

    @override
    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.movie_file(self._key),
            self.url,
        )
