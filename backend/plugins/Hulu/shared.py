# TODO: Validate
"""What the plugin, its importers and its initializer all read Hulu by."""

from __future__ import annotations

from typing import TYPE_CHECKING, override

from app.utils.strict_re import strict_search
from plugins.Hulu.base_files import HuluBaseFiles
from plugins.Hulu.constants import MOVIE_URL_REGEX, SERIES_URL_REGEX, HuluMediaType
from plugins.Hulu.utils import search_url, title_url, title_urls

if TYPE_CHECKING:
    from wholoo.all_movies.models import AllMoviesModel
    from wholoo.all_series.models import AllSeriesModel
    from wholoo.genre.models import GenreModel


class HuluShared(HuluBaseFiles):
    @classmethod
    @override
    def plugin_name(cls) -> str:
        return "Hulu"

    @classmethod
    @override
    def favicon_url(cls) -> str:
        return "https://www.hulu.com/favicon.ico"

    @classmethod
    @override
    def _domain(cls) -> str:
        return "hulu.com"

    @classmethod
    def manual_search_url(cls, query: str) -> str | None:
        return search_url(query)

    # TODO: Validate
    def _create_channel_records(self) -> None:
        self._add_urls_to_channel_by_prefix(self._all_title_urls(), "All Titles")

    def _all_title_urls(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        pages: list[AllSeriesModel | AllMoviesModel | GenreModel] = [
            self.all_series_file().parsed(),
            self.all_movies_file().parsed(),
            *(genre_file.parsed() for genre_file in self.genre_files()),
        ]
        urls: dict[str, None] = {}
        for page in pages:
            for url in title_urls(page):
                match = strict_search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url)
                if series_key := match.group("series_key"):
                    urls[title_url(series_key, HuluMediaType.SERIES)] = None
                else:
                    urls[title_url(match.group("movie_key"), HuluMediaType.MOVIE)] = (
                        None
                    )
        return list(urls)

    def _all_title_keys(self) -> set[str]:
        title_keys: set[str] = set()
        for url in self._all_title_urls():
            match = strict_search(f"{SERIES_URL_REGEX}|{MOVIE_URL_REGEX}", url)
            title_keys.add(match.group("series_key") or match.group("movie_key"))
        return title_keys
