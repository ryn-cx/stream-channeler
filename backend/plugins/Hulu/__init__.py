from __future__ import annotations

import re
from datetime import timedelta
from typing import TYPE_CHECKING, override

from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
)
from plugins.Hulu.movie_importer import HuluMovieImporter
from plugins.Hulu.series_importer import HuluSeriesImporter
from plugins.Hulu.shared import HuluImporter, HuluShared
from plugins.utils.abstract_plugin import AbstractPlugin, InvalidURLError
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Collection
    from datetime import datetime

    from app.titles.models import Title


# TODO: Validate
class Hulu(
    HuluShared,
    AbstractPlugin,
    register=True,
):
    VIDEO_STORE_SCORE = False
    VIDEO_STORE_POPULARITY = False

    # TODO: Validate
    @override
    def similar_title_urls(self, title: Title) -> Collection[str]:
        if title.media_type == MediaType.movie:
            return []
        return [
            HuluSeriesImporter.title_url(str(item.id))
            for component in self.series_file(title.key).components()
            if component.theme == "collection_theme_related"
            for item in component.items
        ]

    # TODO: Validate
    @override
    def _next_plugin_update_at(self) -> datetime:
        return max(self._plugin_files_data_timestamps()) + timedelta(days=7)

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

    # TODO: Validate
    @override
    def _media_importer_from_title(self, title: Title) -> HuluImporter:
        if not title.media_type:  #  Should be impossible.
            msg = "Title.media_type is not set."
            raise AttributeError(msg)

        if title.media_type == MediaType.movie:
            return HuluMovieImporter(self.session, self.plugin, self._file_cache)
        return HuluSeriesImporter(self.session, self.plugin, self._file_cache)
