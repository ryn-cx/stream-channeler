# TODO: Validate
"""HiDive URL handlers."""

from __future__ import annotations

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, override

from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.utils.base_plugin.media_type import MediaTypeURLHandler

if TYPE_CHECKING:
    from plugins.HiDive import HiDive
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class HiDiveURLHandler(MediaTypeURLHandler["HiDive"]):
    """What every HiDive URL has in common."""

    # TODO: Validate
    def __init__(self, plugin: HiDive, url: str, key: str) -> None:
        """Initialize the URL handler."""
        self._key = key
        super().__init__(plugin, url)


# TODO: Validate
class BaseSeriesURLHandler(HiDiveURLHandler):
    """What every URL naming a series has in common."""

    media_type = SERIES_MEDIA_TYPE

    # TODO: Validate
    @abstractmethod
    def _validation_file(self) -> BaseFile[Any]: ...

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(self._validation_file(), self.url)


# TODO: Validate
class SeriesURLHandler(BaseSeriesURLHandler):
    """Series URL handler.

    Example URL https://www.hidive.com/series/1286
    """

    # https://www.hidive.com/series/1286
    _URL_REGEX = r"\/series\/(?P<series_key>\d+)(?:\/|$)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key

    # TODO: Validate
    def _validation_file(self) -> BaseFile[Any]:
        return self.plugin.series_file(self._key)


# HiDive's interface does not do a good job of seperating shows and seasons and if a
# user uses a season URL it should be treated the same as a series URL for a more
# intuitive user experience.
# TODO: Validate
class SeasonURLHandler(BaseSeriesURLHandler):
    """Season URL handler.

    Example URL https://www.hidive.com/season/20022
    """

    # https://www.hidive.com/season/20022
    _URL_REGEX = r"\/season\/(?P<season_key>\d+)(?:\/|$)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        season_data = self.plugin.season_file(self._key).parsed()
        return str(season_data.metadata.series.series_id)

    # TODO: Validate
    def _validation_file(self) -> BaseFile[Any]:
        return self.plugin.season_file(self._key)


# TODO: Validate
class MovieURLHandler(HiDiveURLHandler):
    """Movie URL handler.

    Example URL https://www.hidive.com/video/586784
    """

    media_type = MOVIE_MEDIA_TYPE
    # https://www.hidive.com/video/586784
    _URL_REGEX = r"\/video\/(?P<movie_vod_key>\d+)(?:\/|$)"

    # TODO: Validate
    @property
    @override
    def show_key(self) -> str:
        return self._key

    # TODO: Validate
    @override
    def raise_if_invalid(self) -> None:
        self.plugin.raise_if_invalid_file(self.plugin.vod_file(self._key), self.url)
