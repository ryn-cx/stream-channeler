from __future__ import annotations

import re
from datetime import time, timedelta
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
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
    from sqlmodel import Session

    from app.plugins.models import Plugin
    from app.titles.models import Title


class Hulu(
    HuluShared,
    AbstractPlugin,
    register=False,
):
    @classmethod
    @override  # Overrideen so update_at can be set.
    def _create_initial_plugin_record(cls, session: Session) -> Plugin:
        plugin = super()._create_initial_plugin_record(session)
        plugin.update_at = tz_datetime.now() + timedelta(days=7)
        return plugin

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

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        """Update the plugin with the latest data.

        Downloads the movie/series/genres lists from Hulu then imports the data into the
        database."""
        self._download_if_outdated(self._plugin_files(), plugin.update_at)
        self._create_initial_channel_records()
        data_timestamps = self._plugin_files_data_timestamps()
        new_titles = self._all_title_keys()
        self._mark_mismatched_titles_as_outdated(None, new_titles, data_timestamps)
        plugin.data_timestamp = max(data_timestamps)
        plugin.update_at = staggered_monthly_update_at(plugin.key, tz_datetime.now())
