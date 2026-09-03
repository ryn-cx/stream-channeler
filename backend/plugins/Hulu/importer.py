# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
)
from plugins.Hulu.media import HuluMovie, HuluSeries, MediaMixin
from plugins.Hulu.utils import series_id
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin_v2.importer import BaseImporter

if TYPE_CHECKING:
    from app.shows.models import Show


# TODO: Validate
class HuluSeriesImporter(BaseImporter, HuluSeries):
    _episode_key: str | None

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        self._episode_key = None
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            show_key = match.group("series_id")
            self.raise_if_invalid_file(self.series_file(show_key), url)
            return show_key

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_key = match.group("episode_id")
            episode_hub = self.episode_file(episode_key)
            self.raise_if_invalid_file(episode_hub, url)
            self._episode_key = episode_key
            return series_id(episode_hub.parsed())

        msg = f"Invalid {self.plugin_name()} URL: {url}"
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


# TODO: Validate
class HuluMovieImporter(BaseImporter, HuluMovie):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            show_key = match.group("movie_id")
            self.raise_if_invalid_file(self.movie_file(show_key), url)
            return show_key

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # The episode.key for a movie is the same as the show.key so this is
            # actually returning a show.key.
            show_key = match.group("episode_id")
            self.raise_if_invalid_file(self.movie_file(show_key), url)
            return show_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)


# TODO: Validate
class HuluImporter(BaseImporter, MediaMixin):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        return self._media_importer(url).import_url(url, canonical_show)

    # TODO: Validate
    def _media_importer(self, url: str) -> BaseImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HuluSeriesImporter(self)

        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HuluMovieImporter(self)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_hub = self.episode_file(match.group("episode_id"))
            episode_hub.download_if_outdated()
            if episode_hub.database_record.content:
                return HuluSeriesImporter(self)
            return HuluMovieImporter(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def _parse_url(self, url: str) -> str:
        return self._media_importer(url)._parse_url(url)  # noqa: SLF001
