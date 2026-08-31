# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Hulu.base import HuluBase
from plugins.Hulu.utils import HuluMediaType
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin_v2.workers import Importer

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.seasons.models import Season
    from app.shows.models import Show


# TODO: Validate
class HuluImporter(Importer, HuluBase):
    UUID_REGEX = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
    SLUG_REGEX = r"(?:[a-z0-9-]+-)?"
    _SERIES_URL_REGEX = rf"\/series\/{SLUG_REGEX}(?P<series_id>{UUID_REGEX})"
    _MOVIE_URL_REGEX = rf"\/movie\/{SLUG_REGEX}(?P<movie_id>{UUID_REGEX})"
    _WATCH_URL_REGEX = rf"\/watch\/(?P<episode_id>{UUID_REGEX})"

    _show_key: str

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (cls._SERIES_URL_REGEX, cls._MOVIE_URL_REGEX, cls._WATCH_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            self._show_key = match.group("series_id")
            self._media_type = HuluMediaType.SERIES
            self.raise_if_invalid_file(self.series_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            self._show_key = match.group("movie_id")
            self._media_type = HuluMediaType.MOVIE
            self.raise_if_invalid_file(self.movie_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._WATCH_URL_REGEX, url):
            episode_key = match.group("episode_id")
            episode_hub = self.episode_hub_file(episode_key)
            episode_hub.download_if_outdated()
            if episode_hub.database_record.content:
                self._show_key = episode_hub.series_id()
                self._media_type = HuluMediaType.SERIES
                self.raise_if_invalid_file(episode_hub, url)
            else:
                self._show_key = episode_key
                self._media_type = HuluMediaType.MOVIE
                self.raise_if_invalid_file(self.movie_file(episode_key), url)
            return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _set_record(self, record: Show | Season | Episode) -> None:
        super()._set_record(record)
        self._set_media_type_from_show(self.show)
