# TODO: Validate
"""What the plugin, its importers and its initializer all read Hulu by."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.utils.strict_re import strict_search
from plugins.Hulu.base_files import HuluBaseFiles
from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    HuluMediaType,
)
from plugins.Hulu.utils import title_url, title_urls

if TYPE_CHECKING:
    from wholoo.all_movies.models import AllMoviesModel
    from wholoo.all_series.models import AllSeriesModel
    from wholoo.genre.models import GenreModel


# TODO: Validate
class HuluShared(HuluBaseFiles):
    # TODO: Validate
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    # TODO: Validate
    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    # TODO: Validate
    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    # TODO: Validate
    def create_initial_channel_records(self) -> None:
        self.add_new_urls_to_channel(
            "All Titles",
            self._title_urls_from_plugin_files(),
        )

    # TODO: Validate
    def _title_urls_from_plugin_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        pages: list[AllSeriesModel | AllMoviesModel | GenreModel] = [
            self.all_series_file().parsed(),
            self.all_movies_file().parsed(),
            *(genre_file.parsed() for genre_file in self.genre_files()),
        ]
        urls: dict[str, None] = {}
        for page in pages:
            for url in title_urls(page):
                if match := re.search(SERIES_URL_REGEX, url):
                    series_key = match.group("title_key")
                    urls[title_url(series_key, HuluMediaType.SERIES)] = None
                else:
                    movie_key = strict_search(MOVIE_URL_REGEX, url).group("title_key")
                    urls[title_url(movie_key, HuluMediaType.MOVIE)] = None
        return list(urls)

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> set[str]:
        title_keys: set[str] = set()
        for url in self._title_urls_from_plugin_files():
            match = re.search(SERIES_URL_REGEX, url) or strict_search(
                MOVIE_URL_REGEX,
                url,
            )
            title_keys.add(match.group("title_key"))
        return title_keys
