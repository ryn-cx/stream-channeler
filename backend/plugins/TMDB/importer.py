# TODO: Validate
"""Reading a title in, whether a URL named it or an id did.

A title is read again on a timer, and reading one in full is a file per season
whether anything moved or not. What TMDB's changes endpoints answer is which
records moved, so a read starts by asking that and goes no further than the
records named.
"""

from __future__ import annotations

import re
from abc import ABC
from typing import override

from app.canonical_media.keys import (
    tmdb_show_key,
)
from app.media.media_type import TMDBMediaType
from app.shows.models import Show
from plugins.TMDB.media import MediaMixin, TMDBMedia, TMDBMovie, TMDBSeries
from plugins.utils.abstract_plugin import (
    InvalidURLError,
    URLImportResult,
)
from plugins.utils.base_plugin_v3.importer import BaseImporter

# from plugins.WatchMode import WatchMode  # noqa: ERA001


# TODO: Validate
def _title_url_regex(media_type: TMDBMediaType) -> str:
    return rf"\/{media_type}\/(?P<{media_type}_tmdb_id>\d+)"


MOVIE_URL_REGEX = _title_url_regex(TMDBMediaType.movie)
TV_URL_REGEX = _title_url_regex(TMDBMediaType.tv)


# TODO: Validate
class TMDBTitleImporter(BaseImporter, TMDBMedia, ABC):
    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        # TMDB should always be canonical so if it is imported with a caonical_show
        # something has gone wrong.
        if canonical_show is not None:
            msg = "canonical_show should be None when importing TMDB URLs."
            raise InvalidURLError(msg)

        show_key = self._url_to_show_key(url)
        existing_show = self._preload_show(
            show_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_show:
            existing_show = self.upsert_show(self.source, show_key)
            self._import_media_from_other_websites(show_key, existing_show)

        return self._import_results(existing_show)


# TODO: Validate
class TMDBSeriesImporter(TMDBTitleImporter, TMDBSeries):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TV_URL_REGEX,)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        match = re.match(self._domain_regex() + TV_URL_REGEX, url)
        if match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_id = int(match.group(f"{TMDBMediaType.tv}_tmdb_id"))
        self.raise_if_invalid_file(self.tv_series_details_file(tmdb_id), url)
        return tmdb_show_key(TMDBMediaType.tv, tmdb_id)


# TODO: Validate
class TMDBMovieImporter(TMDBTitleImporter, TMDBMovie):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def _url_to_show_key(self, url: str) -> str:
        match = re.match(self._domain_regex() + MOVIE_URL_REGEX, url)
        if match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_id = int(match.group(f"{TMDBMediaType.movie}_tmdb_id"))
        self.raise_if_invalid_file(self.movies_details_file(tmdb_id), url)
        return tmdb_show_key(TMDBMediaType.movie, tmdb_id)


# TODO: Validate
class TMDBImporter(BaseImporter, MediaMixin):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX, TV_URL_REGEX)

    # TODO: Validate
    @override
    def import_url(
        self,
        url: str,
        canonical_show: Show | None = None,
    ) -> list[URLImportResult]:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return TMDBMovieImporter(self).import_url(url, canonical_show)

        if re.match(domain_regex + TV_URL_REGEX, url):
            return TMDBSeriesImporter(self).import_url(url, canonical_show)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)
