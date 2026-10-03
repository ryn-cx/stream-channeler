# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, override

from app.utils.strict_re import strict_search
from plugins.Hulu.constants import (
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
    HuluMediaType,
)
from plugins.Hulu.files import AllMovies, AllSeries, Genre, Genres
from plugins.Hulu.series_importer import HuluSeriesImporter
from plugins.Hulu.shared import HuluShared
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.updater import BasePluginUpdater

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Sequence
    from datetime import datetime

    from wholoo.all_movies.models import AllMoviesModel
    from wholoo.all_series.models import AllSeriesModel
    from wholoo.genre.models import GenreModel
    from wholoo.genres.models import GenresModel

    from app.titles.models import Title


# TODO: Validate
class HuluUpdater(HuluShared, BasePluginUpdater):
    def all_series_file(self) -> AllSeries:
        return self._cached_file(AllSeries)

    def all_movies_file(self) -> AllMovies:
        return self._cached_file(AllMovies)

    def genres_file(self) -> Genres:
        return self._cached_file(Genres)

    def genre_file(self, genre_id: str) -> Genre:
        return self._cached_file(Genre, genre_id)

    # TODO: Validate
    def genre_files(self) -> list[Genre]:
        self.genres_file().download_if_outdated()
        return [
            self.genre_file(genre_id)
            for genre_id in self.genre_ids(self.genres_file().parsed())
        ]

    # TODO: Validate
    @staticmethod
    def genre_ids(page: GenresModel) -> list[str]:
        return [item.href.removeprefix("/hub/") for item in page.items]

    @override
    def _plugin_files(self) -> Sequence[AllSeries | AllMovies | Genres | Genre]:
        return [
            self.all_series_file(),
            self.all_movies_file(),
            self.genres_file(),
            *self.genre_files(),
        ]

    # TODO: Validate
    @override
    def _title_urls_from_files(self) -> list[str]:
        self._download_if_outdated(self._plugin_files())
        pages: list[AllSeriesModel | AllMoviesModel | GenreModel] = [
            self.all_series_file().parsed(),
            self.all_movies_file().parsed(),
            *(genre_file.parsed() for genre_file in self.genre_files()),
        ]
        urls: dict[str, None] = {}
        for page in pages:
            for url in self.title_urls(page):
                if match := re.search(SERIES_URL_REGEX, url):
                    series_key = match.group("title_key")
                    urls[self.build_url(f"{HuluMediaType.SERIES}/{series_key}")] = None
                else:
                    movie_key = strict_search(MOVIE_URL_REGEX, url).group("title_key")
                    urls[self.build_url(f"{HuluMediaType.MOVIE}/{movie_key}")] = None
        return list(urls)

    # TODO: Validate
    @classmethod
    def title_urls(
        cls,
        page: AllSeriesModel | AllMoviesModel | GenreModel,
    ) -> list[str]:
        """Return all title URLs from the given page."""
        return [cls.build_url(item.href) for item in page.items]

    # TODO: Validate
    def _title_keys_from_plugin_files(self) -> set[str]:
        title_keys: set[str] = set()
        for url in self._title_urls_from_files():
            match = re.search(SERIES_URL_REGEX, url) or strict_search(
                MOVIE_URL_REGEX,
                url,
            )
            title_keys.add(match.group("title_key"))
        return title_keys

    # TODO: Validate
    @override
    def _mark_mismatched_titles_as_outdated(
        self,
        source_key: str | None,
        new_title_keys: Iterable[str],
        data_timestamp: datetime,
    ) -> None:
        listed_title_keys = set(new_title_keys)
        for source in self._preload_sources(source_key, preload_titles=True):
            for title in source.titles:
                if title.key in listed_title_keys and title.deleted_at is not None:
                    title.set_update_at(data_timestamp)

    # TODO: Validate
    def similar_title_urls(self, title: Title) -> Collection[str]:
        if title.media_type == MediaType.movie:
            return []
        return [
            HuluSeriesImporter.title_url(str(item.id))
            for component in self.series_file(title.key).components()
            if component.theme == "collection_theme_related"
            for item in component.items
        ]
