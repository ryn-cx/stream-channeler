# TODO: Validate
from __future__ import annotations

import re
from typing import override

from app.shows.models import Show
from plugins.Tubi.constants import CONTENT_ID_REGEX, SLUG_REGEX
from plugins.Tubi.utils import HelperMixin
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.plugin import ReadURLPlugin


# TODO: Validate
class ImportURLMixin(HelperMixin, ReadURLPlugin, register=False):
    # https://tubitv.com/movies/100029837/megamind
    _MOVIE_URL_REGEX = (
        rf"\/movies\/(?P<movie_id>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
    )
    # https://tubitv.com/series/300006854/scooby-doo-where-are-you
    _SERIES_URL_REGEX = (
        rf"\/series\/(?P<series_id>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
    )
    # https://tubitv.com/tv-shows/595036/s01-e01-what-a-night-for-a-knight
    _EPISODE_URL_REGEX = (
        rf"\/tv-shows\/(?P<episode_id>{CONTENT_ID_REGEX}){SLUG_REGEX}(?:\/|$)"
    )

    _episode_key: str | None

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            cls._MOVIE_URL_REGEX,
            cls._SERIES_URL_REGEX,
            cls._EPISODE_URL_REGEX,
        )

    # TODO: Validate
    @override
    def _read_url(self, url: str) -> None:
        domain_regex = self._domain_regex()
        self._episode_key = None

        if match := re.match(domain_regex + self._MOVIE_URL_REGEX, url):
            self._show_key = match.group("movie_id")
            self.raise_if_invalid_file(self.content_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._SERIES_URL_REGEX, url):
            self._show_key = match.group("series_id")
            self.raise_if_invalid_file(self.content_file(self._show_key), url)
            return

        if match := re.match(domain_regex + self._EPISODE_URL_REGEX, url):
            episode_key = match.group("episode_id")
            self.raise_if_invalid_file(self.content_file(episode_key), url)
            series_id = self.content_file(episode_key).parsed().series_id
            if series_id is None:
                msg = f"Invalid {self.plugin_key()} URL: {url}"
                raise InvalidURLError(msg)
            self._episode_key = episode_key
            self._show_key = series_id
            return

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _import_results(self, show: Show) -> list[URLImportResult]:
        if self._episode_key is None:
            return super()._import_results(show)

        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == self._episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]

        msg = f"Episode {self._episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)
