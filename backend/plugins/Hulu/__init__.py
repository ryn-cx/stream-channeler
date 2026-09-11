from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
    HuluMediaType,
)
from plugins.Hulu.importer import HuluImporter, HuluMovieImporter, HuluSeriesImporter
from plugins.Hulu.shared import HuluShared
from plugins.Hulu.utils import title_url
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError

if TYPE_CHECKING:
    from datetime import datetime

    from app.titles.models import Title


# TODO: Validate
class Hulu(
    HuluShared,
    AbstractPlugin,
    register=True,
):
    # TODO: Validate
    @override
    def _next_plugin_update_at(self) -> datetime:
        return max(self._plugin_files_data_timestamps()) + timedelta(days=7)

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    @override
    def _media_importer_from_url(self, url: str) -> HuluImporter:
        domain_regex = self._domains_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)

        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            # Movies and series use the same URL format for individual episodes. Only a
            # series episode is served by the episode endpoint, so a movie is what is
            # left when that endpoint has nothing for the key.
            episode_file = self.episode_file(match.group("episode_key"))
            episode_file.download_if_outdated()
            if episode_file.record_content:
                return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)

        # Should only occur on invalid episode URLs.
        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def _media_importer_from_title(self, title: Title) -> HuluImporter:
        if not title.media_type:  #  Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == "Movie":
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)
        return HuluSeriesImporter(self.session, self.plugin, self._file_cache)

    @override
    def search_for_title_url(
        self,
        name: str,
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        hulu_media_type = (
            HuluMediaType.MOVIE
            if media_type == TMDBMediaType.movie
            else HuluMediaType.SERIES
        )
        search_file = self.search_file(name)
        search_file.download_if_outdated()
        for result in search_file.parsed().results:
            if result.metrics_info.target_type == hulu_media_type:
                return title_url(result.metrics_info.target_id, hulu_media_type)
        return None
