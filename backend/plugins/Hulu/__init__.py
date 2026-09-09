# TODO: Validate
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
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin
    from app.titles.models import Title


# TODO: Validate
class Hulu(
    HuluShared,
    BaseImporter,
    AbstractPlugin,
    register=False,
):
    # TODO: Validate
    # Overrideen so update_at can be set.
    @classmethod
    @override
    def _create_initial_plugin_record(cls, session: Session) -> Plugin:
        plugin = super()._create_initial_plugin_record(session)
        plugin.update_at = tz_datetime.now() + timedelta(days=7)
        return plugin

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def _validate_url(self, url: str) -> None:
        domain_regex = self._domains_regex()
        for url_regex in (SERIES_URL_REGEX, MOVIE_URL_REGEX):
            if re.match(domain_regex + url_regex, url):
                return

        redirect_url = self._video_redirect_url(url)
        for url_regex in (SERIES_URL_REGEX, MOVIE_URL_REGEX):
            if re.search(url_regex, redirect_url):
                return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _video_redirect_url(self, url: str) -> str:
        # Movies and series use the same URL format for individual episodes. When trying
        # to access the URL anonymously the user is directed to the title URL which
        # contains the media type information.
        if not (match := re.match(self._domains_regex() + VIDEO_URL_REGEX, url)):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        redirect_file = self.watch_redirect_file(match.group("episode_key"))
        redirect_file.download_if_outdated()
        return redirect_file.parsed()

    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> HuluImporter:
        domain_regex = self._domains_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)

        if re.search(SERIES_URL_REGEX, self._video_redirect_url(url)):
            return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
        return HuluMovieImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> HuluImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)
        return HuluSeriesImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    @override
    def search_for_title_url(
        self,
        names: list[str],
        media_type: TMDBMediaType,
        year: int | None = None,
    ) -> str | None:
        hulu_media_type = (
            HuluMediaType.MOVIE
            if media_type == TMDBMediaType.movie
            else HuluMediaType.SERIES
        )
        search_file = self.search_file(names[0])
        search_file.download_if_outdated()
        for group in search_file.parsed().groups:
            for result in group.results:
                if result.metrics_info.target_type == hulu_media_type:
                    return title_url(result.metrics_info.target_id, hulu_media_type)
        return None

    # TODO: Validate
    @override
    def update_plugin(self, plugin: Plugin) -> None:
        self._download_if_outdated(self._plugin_files(), plugin.update_at)
        self._create_initial_channel_records()
        data_timestamps = self._plugin_files_data_timestamps()
        new_titles = self._all_title_keys()
        self._mark_mismatched_titles_as_outdated(None, new_titles, data_timestamps)
        plugin.data_timestamp = max(data_timestamps)
        plugin.update_at = staggered_monthly_update_at(plugin.key, tz_datetime.now())
