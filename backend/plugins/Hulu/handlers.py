from __future__ import annotations

from typing import TYPE_CHECKING

from plugins.utils.base_plugin.url import URLHandler

if TYPE_CHECKING:
    from plugins.Hulu import Hulu


class HuluURLHandler(URLHandler["Hulu"]):
    content_type: str

    def __init__(self, plugin: Hulu, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)

    @property
    def show_key(self) -> str:
        return f"{self.content_type}/{self._key}"


class SeriesURLHandler(HuluURLHandler):
    content_type = "series"
    # https://www.hulu.com/series/fdeb1018-4472-442f-ba94-fb087cdea069
    _PATH_REGEX = r"\/series\/(?P<series_id>[0-9a-f\-]+)"

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.series_file(self._key),
            self.url,
        )


class MovieURLHandler(HuluURLHandler):
    content_type = "movie"
    # https://www.hulu.com/movie/4ee4f57e-19bd-493f-96f9-ad3e753af981
    _PATH_REGEX = r"\/movie\/(?P<movie_id>[0-9a-f\-]+)"

    def validate_url(self) -> None:
        self.plugin.raise_if_invalid_file(
            self.plugin.movie_file(self._key),
            self.url,
        )
