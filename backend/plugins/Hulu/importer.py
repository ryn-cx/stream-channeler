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
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    def _url_to_show_and_episode_keys(self, url: str) -> tuple[str, str | None]:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            show_key = match.group("series_key")
            self.raise_if_invalid_file(self.series_file(show_key), url)
            return show_key, None

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            episode_key = match.group("episode_key")
            episode_hub = self.episode_file(episode_key)
            self.raise_if_invalid_file(episode_hub, url)
            return series_id(episode_hub.parsed()), episode_key

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def _url_to_show_key(self, url: str) -> str:
        return self._url_to_show_and_episode_keys(url)[0]

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        show_key, episode_key = self._url_to_show_and_episode_keys(url)
        if show := self._preload_show(show_key).one_or_none():
            return self._import_results(show, episode_key)

        _cache = self._download_show_files_and_children(show_key)
        show = self.upsert_show(self._url_source(), show_key)
        return self._import_results(show, episode_key)

    # TODO: Validate
    @override
    def _import_results(
        self,
        show: Show,
        episode_key: str | None = None,
    ) -> list[URLImportResult]:
        if episode_key is None:
            return super()._import_results(show)

        for season in show.seasons:
            for episode in season.episodes:
                if episode.key == episode_key:
                    return [URLImportResult.episode_import_results(show, [episode])]

        msg = f"Episode {episode_key} not found in show {show.key}"
        raise InvalidURLError(msg)


# TODO: Validate
class HuluMovieImporter(BaseImporter, HuluMovie):
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + MOVIE_URL_REGEX, url):
            show_key = match.group("movie_key")
        elif match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # The episode.key for a movie is the same as the show.key so this is
            # actually returning a show.key.
            show_key = match.group("episode_key")
        else:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self.raise_if_invalid_file(self.movie_file(show_key), url)
        return show_key


class HuluImporter(BaseImporter, MediaMixin):
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HuluSeriesImporter(self).import_url(url)

        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HuluMovieImporter(self).import_url(url)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            watch_redirect = self.watch_redirect_file(match.group("episode_key"))
            watch_redirect.download_if_outdated()
            location = watch_redirect.location()
            if location and re.search(SERIES_URL_REGEX, location):
                return HuluSeriesImporter(self).import_url(url)
            if location and re.search(MOVIE_URL_REGEX, location):
                return HuluMovieImporter(self).import_url(url)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
