# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.HiDive.base import HiDiveBase
from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.importer import Importer

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class HiDiveImporter(Importer, HiDiveBase):
    # https://www.hidive.com/series/1286
    _SERIES_URL_REGEX = r"\/series\/(?P<series_key>\d+)(?:\/|$)"
    # https://www.hidive.com/season/20022
    _SEASON_URL_REGEX = r"\/season\/(?P<season_key>\d+)(?:\/|$)"
    # https://www.hidive.com/video/586784
    _MOVIE_URL_REGEX = r"\/video\/(?P<movie_vod_key>\d+)(?:\/|$)"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            cls._SERIES_URL_REGEX,
            cls._SEASON_URL_REGEX,
            cls._MOVIE_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            show_key = match.group("series_key")
            self._media_type = SERIES_MEDIA_TYPE
            self.raise_if_invalid_file(self.series_file(show_key), url)
            return show_key

        # HiDive's interface does not do a good job of seperating shows and seasons
        # and if a user uses a season URL it should be treated the same as a series
        # URL for a more intuitive user experience.
        if match := re.match(domain_regex + self._SEASON_URL_REGEX, url):
            season_key = match.group("season_key")
            self._media_type = SERIES_MEDIA_TYPE
            self.raise_if_invalid_file(self.season_file(season_key), url)
            season_data = self.season_file(season_key).parsed()
            return str(season_data.metadata.series.series_id)

        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            show_key = match.group("movie_vod_key")
            self._media_type = MOVIE_MEDIA_TYPE
            self.raise_if_invalid_file(self.vod_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _set_record(self, record: Show | Season | Episode) -> None:
        super()._set_record(record)
        self._set_media_type_from_show(self.show)
