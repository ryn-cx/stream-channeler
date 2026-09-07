from __future__ import annotations

from datetime import time, timedelta
import re
from typing import TYPE_CHECKING, override

from app.media.media_type import TMDBMediaType
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.Hulu.importer import HuluImporter, HuluMovieImporter, HuluSeriesImporter
from plugins.Hulu.shared import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
    HuluShared,
)
from plugins.Hulu.utils import HuluMediaType, title_url
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    InvalidURLError,
    TMDBLookupInfo,
)
from plugins.utils.base_plugin.base import BaseReadURL
from plugins.utils.base_plugin.initialize import BasePluginInitializer

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin
    from app.titles.models import Title


class HuluInitializer(HuluShared, BasePluginInitializer):
    @classmethod
    @override
    def _create_plugin_record(cls, session: Session) -> Plugin:
        plugin = super()._create_plugin_record(session)
        plugin.update_at = tz_datetime.now() + timedelta(days=7)
        return plugin


# TODO: Validate
class Hulu(
    HuluShared,
    BaseReadURL,
    AbstractPlugin,
    register=True,
):
    initializer = HuluInitializer

    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    @override
    def media_importer_from_url(self, url: str) -> HuluImporter:
        domain_regex = self._domain_regex()
        if re.match(domain_regex + SERIES_URL_REGEX, url):
            return HuluSeriesImporter(self)
        if re.match(domain_regex + MOVIE_URL_REGEX, url):
            return HuluMovieImporter(self)

        # Watch URLs are the same for movies and series so extra analysis needs to
        # be done.
        if match := re.match(domain_regex + VIDEO_URL_REGEX, url):
            redirect_url = self.watch_redirect_file(
                match.group("episode_key"),
            ).parsed()
            if re.search(SERIES_URL_REGEX, redirect_url):
                return HuluSeriesImporter(self)
            if re.search(MOVIE_URL_REGEX, redirect_url):
                return HuluMovieImporter(self)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def media_importer_from_title(self, title: Title) -> HuluImporter:
        if not title.media_type:
            msg = "Title.media_type is not set."
            raise AttributeError(msg)
        if title.media_type == "Movie":
            return HuluMovieImporter(self)
        return HuluSeriesImporter(self)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        title = self._preload_title(title_key).one()
        return self.media_importer_from_title(title).tmdb_lookup_info(title_key)

    @override
    def search_for_url(
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
        for group in self.search_file(names[0]).parsed().groups:
            for result in group.results:
                if result.metrics_info.target_type == hulu_media_type:
                    return title_url(result.metrics_info.target_id, hulu_media_type)
        return None

    @override
    def update_plugin(self, plugin: Plugin) -> None:
        self._download_if_outdated(self._plugin_files(), plugin.update_at)
        self._create_channel_records()
        data_timestamps = self.plugin_data_timestamps()
        new_titles = self._all_title_keys()
        self._mark_mismatched_titles_as_outdated(None, new_titles, data_timestamps)
        plugin.data_timestamp = max(data_timestamps)
        plugin.update_at = staggered_monthly_update_at(plugin.key, tz_datetime.now())
