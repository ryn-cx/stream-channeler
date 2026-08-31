# TODO: Validate
from __future__ import annotations

import re
from typing import override

from plugins.Hulu.constants import (
    MOVIE_MEDIA_TYPE,
    SERIES_MEDIA_TYPE,
    SLUG_REGEX,
    UUID_REGEX,
)
from plugins.Hulu.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.media_type import MediaTypeReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, MediaTypeReadURLPlugin, register=False):
    _SERIES_URL_REGEX = rf"\/series\/{SLUG_REGEX}(?P<series_id>{UUID_REGEX})"
    _MOVIE_URL_REGEX = rf"\/movie\/{SLUG_REGEX}(?P<movie_id>{UUID_REGEX})"
    _WATCH_URL_REGEX = rf"\/watch\/(?P<episode_id>{UUID_REGEX})"

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            cls._SERIES_URL_REGEX,
            cls._MOVIE_URL_REGEX,
            cls._WATCH_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            self._show_key = match.group("series_id")
            self._media_type = SERIES_MEDIA_TYPE
            self.raise_if_invalid_file(self.series_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            self._show_key = match.group("movie_id")
            self._media_type = MOVIE_MEDIA_TYPE
            self.raise_if_invalid_file(self.movie_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._WATCH_URL_REGEX, url):
            episode_key = match.group("episode_id")
            episode_hub = self.episode_hub_file(episode_key)
            episode_hub.download_if_outdated()
            if episode_hub.database_record.content:
                self._show_key = episode_hub.series_id()
                self._media_type = SERIES_MEDIA_TYPE
                self.raise_if_invalid_file(episode_hub, url)
            else:
                self._show_key = episode_key
                self._media_type = MOVIE_MEDIA_TYPE
                self.raise_if_invalid_file(self.movie_file(episode_key), url)
            return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)
