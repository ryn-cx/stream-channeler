# TODO: Validate
from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, override

from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.HiDive import HiDive
    from plugins.utils.base_plugin.files import BaseFile


class HiDiveURLHandler(MediaTypeURLHandler["HiDive"]):
    def __init__(self, plugin: HiDive, url: str, key: str) -> None:
        self._key = key
        super().__init__(plugin, url)


class BaseSeriesURLHandler(HiDiveURLHandler):
    media_type = "Series"

    @abstractmethod
    def _validation_file(self) -> BaseFile[Any]: ...

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(self._validation_file(), self.url)


class SeriesURLHandler(BaseSeriesURLHandler):
    # https://www.hidive.com/series/1286
    _URL_REGEX = r"\/series\/(?P<series_key>\d+)(?:\/|$)"

    @property
    @override
    def show_key(self) -> str:
        return self._key

    def _validation_file(self) -> BaseFile[Any]:
        return self.plugin.series_file(self._key)


# HiDive's interface does not do a good job of seperating shows and seasons and if a
# user uses a season URL it should be treated the same as a series URL for a more
# intuitive user experience.
class SeasonURLHandler(BaseSeriesURLHandler):
    # https://www.hidive.com/season/20022
    _URL_REGEX = r"\/season\/(?P<season_key>\d+)(?:\/|$)"

    @property
    @override
    def show_key(self) -> str:
        season_data = self.plugin.season_file(self._key).parsed()
        return str(season_data.metadata.series.series_id)

    def _validation_file(self) -> BaseFile[Any]:
        return self.plugin.season_file(self._key)


class MovieURLHandler(HiDiveURLHandler):
    media_type = "Movie"
    # https://www.hidive.com/video/586784
    _URL_REGEX = r"\/video\/(?P<movie_vod_key>\d+)(?:\/|$)"

    @property
    @override
    def show_key(self) -> str:
        return self._key

    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(self.plugin.vod_file(self._key), self.url)
