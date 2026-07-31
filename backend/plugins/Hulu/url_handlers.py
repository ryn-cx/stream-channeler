# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, override

from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.Hulu import Hulu

_UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
_SLUG_REGEX = r"(?:[a-z0-9-]+-)?"


class HuluURLHandler(MediaTypeURLHandler["Hulu"]):
    def __init__(self, plugin: Hulu, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    @override
    def show_key(self) -> str:
        return self._key


class SeriesURLHandler(HuluURLHandler):
    media_type = "series"
    # https://www.hulu.com/series/fdeb1018-4472-442f-ba94-fb087cdea069
    # https://www.hulu.com/series/rick-and-morty-4e0f6374-fc81-4da2-b7a9-f7f8c29e7acc
    _URL_REGEX = rf"\/series\/{_SLUG_REGEX}(?P<series_id>{_UUID_REGEX})"

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.series_file(self._key),
            self.url,
        )


class MovieURLHandler(HuluURLHandler):
    media_type = "movie"
    # https://www.hulu.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981
    # https://www.hulu.com/movie/the-wolf-of-wallstreet-4ee4f57e-19bd-493f-96f9-ad3e753af981
    _URL_REGEX = rf"\/movie\/{_SLUG_REGEX}(?P<movie_id>{_UUID_REGEX})"

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.movie_file(self._key),
            self.url,
        )
