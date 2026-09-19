# TODO: Validate
"""What the plugin, its importers and its initializer all read Hulu by."""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import TYPE_CHECKING, override
from urllib.parse import quote
from uuid import UUID

from wholoo.all_movies.models import AllMoviesModel
from wholoo.all_series.models import AllSeriesModel
from wholoo.genre.models import GenreModel
from wholoo.genres.models import GenresModel
from wholoo.movies.models import Component as MovieComponent
from wholoo.movies.models import Details as MovieDetails
from wholoo.movies.models import Item as MovieCollectionItem
from wholoo.season.models import Item, SeasonModel
from wholoo.tv.models import Component as SeriesComponent
from wholoo.tv.models import Details as TVDetails
from wholoo.tv.models import Item as SeriesCollectionItem
from wholoo.tv.models import TVModel

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils.strict_re import strict_search
from plugins.Hulu.constants import (
    EPISODES_COLLECTION_IDS,
    MOVIE_URL_REGEX,
    RECOMMENDATIONS_TOPIC,
    SERIES_URL_REGEX,
    VIDEO_URL_REGEX,
    HuluMediaType,
)
from plugins.Hulu.files import (
    AllMovies,
    AllSeries,
    Genre,
    Genres,
    Movie,
    Series,
)
from plugins.Hulu.files import Episode as EpisodeFile
from plugins.Hulu.files import Season as SeasonFile
from plugins.utils.base_plugin.base import BasePlugin
from plugins.utils.base_plugin.importer import BaseImporter

if TYPE_CHECKING:
    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult


# TODO: Validate
def build_url(path: str) -> str:
    return f"https://hulu.com/{path.lstrip('/')}"


# TODO: Validate
def episode_url(episode_key: str) -> str:
    return build_url(f"watch/{episode_key}")


# TODO: Validate
def image_url(path: str | None) -> str | None:
    if path is None:
        return None
    operations = quote('[{"resize":"1920x1920|max"},{"format":"webp"}]', safe=":,")
    return f"{path}&operations={operations}"


# TODO: Validate
def thumbnail_url(path: str | None) -> str | None:
    if path is None:
        return None
    operations = quote('[{"resize":"600x600|max"},{"format":"webp"}]', safe=":,")
    return f"{path}&operations={operations}"


# TODO: Validate
def build_season_key(title_key: str, season_number: int) -> str:
    return f"{title_key}:{season_number}"


# TODO: Validate
def split_season_key(key: str) -> tuple[str, int]:
    title_key, _, season_number = key.rpartition(":")
    return title_key, int(season_number)


# TODO: Validate
def season_numbers(series: TVModel) -> list[int]:
    numbers: dict[int, None] = {}
    for component in series.components:
        for item in component.items:
            grouping = item.series_grouping_metadata
            if grouping is not None:
                numbers[grouping.season_number] = None
    return list(numbers)


# TODO: Validate
def season_items(season: SeasonModel) -> list[Item]:
    items: dict[UUID, Item] = {}
    for item in season.items:
        items.setdefault(item.id, item)
    return list(items.values())


# TODO: Validate
def title_urls(page: AllSeriesModel | AllMoviesModel | GenreModel) -> list[str]:
    """Return all title URLs from the given page."""
    return [build_url(item.href) for item in page.items]


# TODO: Validate
def genre_ids(page: GenresModel) -> list[str]:
    return [item.href.removeprefix("/hub/") for item in page.items]


# TODO: Validate
def title_plan(details: TVDetails | MovieDetails) -> tuple[str, bool] | None:
    vod_items = details.vod_items
    if vod_items is None:
        return None
    bundle = vod_items.focus.entity.bundle
    # I have no idea why but these specifically need whitelisting.
    is_subscription = bundle.package_id not in (1, 2, 33) and (
        bundle.network_name != "Sony"
    )
    return bundle.network_name, is_subscription


# TODO: Validate
def collection_season_key(title_key: str, component_id: str) -> str:
    return f"{title_key}:collection-{component_id}"


# TODO: Validate
def is_collection_season_key(season_key: str) -> bool:
    return ":collection-" in season_key


# TODO: Validate
def split_collection_season_key(season_key: str) -> tuple[str, str]:
    title_key, _, component_id = season_key.partition(":collection-")
    return title_key, component_id


# TODO: Validate
def title_item_url(
    item: SeriesCollectionItem | MovieCollectionItem,
) -> str | None:
    if item.field_type == HuluMediaType.SERIES:
        return build_url(f"{HuluMediaType.SERIES}/{item.id}")
    if item.field_type == HuluMediaType.MOVIE:
        return build_url(f"{HuluMediaType.MOVIE}/{item.id}")
    return None


# TODO: Validate
def watch_components(
    components: Sequence[SeriesComponent | MovieComponent],
) -> list[SeriesComponent | MovieComponent]:
    return [
        component
        for component in components
        if component.id not in EPISODES_COLLECTION_IDS
        and component.items
        and component.items[0].field_type in ("episode", "extra")
    ]


# TODO: Validate
def watch_component(
    components: Sequence[SeriesComponent | MovieComponent],
    component_id: str,
) -> SeriesComponent | MovieComponent:
    return next(
        component
        for component in watch_components(components)
        if component.id == component_id
    )


# TODO: Validate
def collection_urls(
    components: Sequence[SeriesComponent | MovieComponent],
) -> list[str]:
    urls: dict[str, None] = {}
    for component in components:
        if component.id in EPISODES_COLLECTION_IDS:
            continue
        for item in component.items:
            if url := title_item_url(item):
                urls[url] = None
    return list(urls)


# TODO: Validate
class HuluShared(BasePlugin):
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
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, MOVIE_URL_REGEX, VIDEO_URL_REGEX)

    # TODO: Validate
    def episode_file(self, episode_key: str) -> EpisodeFile:
        return self._cached_file(EpisodeFile, episode_key)

    def all_series_file(self) -> AllSeries:
        return self._cached_file(AllSeries)

    def all_movies_file(self) -> AllMovies:
        return self._cached_file(AllMovies)

    def genres_file(self) -> Genres:
        return self._cached_file(Genres)

    def genre_file(self, genre_id: str) -> Genre:
        return self._cached_file(Genre, genre_id)

    def genre_files(self) -> list[Genre]:
        self.genres_file().download_if_outdated()
        return [
            self.genre_file(genre_id)
            for genre_id in genre_ids(self.genres_file().parsed())
        ]

    def series_file(self, series_id: str) -> Series:
        return self._cached_file(Series, series_id)

    def movie_file(self, movie_id: str) -> Movie:
        return self._cached_file(Movie, movie_id)

    def season_file(self, series_id: str, season_number: int) -> SeasonFile:
        return self._cached_file(SeasonFile, series_id, season_number)

    @override
    def _plugin_files(self) -> Sequence[AllSeries | AllMovies | Genres | Genre]:
        return [
            self.all_series_file(),
            self.all_movies_file(),
            self.genres_file(),
            *self.genre_files(),
        ]

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
                    urls[build_url(f"{HuluMediaType.SERIES}/{series_key}")] = None
                else:
                    movie_key = strict_search(MOVIE_URL_REGEX, url).group("title_key")
                    urls[build_url(f"{HuluMediaType.MOVIE}/{movie_key}")] = None
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


# TODO: Validate
class HuluImporterChannels(HuluShared, BaseImporter, ABC):
    # TODO: Validate
    @abstractmethod
    def _media_type_name(self) -> str: ...

    # TODO: Validate
    @abstractmethod
    @override
    def _title_files(self, title_key: str) -> Sequence[Series | Movie]: ...

    # TODO: Validate
    @abstractmethod
    def _title_components(
        self,
        title_key: str,
    ) -> Sequence[SeriesComponent | MovieComponent]: ...

    # TODO: Validate
    @abstractmethod
    def _title_record(self, source: Source, title_key: str) -> Title: ...

    # TODO: Validate
    @abstractmethod
    def _upsert_title_seasons(self, title: Title) -> None: ...

    # TODO: Validate
    @override
    def add_title_to_plugin_channels(self, title: Title) -> None:
        if not title.url:  # Should be impossible.
            msg = "Title.url is not set."
            raise AttributeError(msg)

        details = self._title_files(title.key)[0].details()
        plan = title_plan(details)
        channel_keys = ["All Titles", self._media_type_name()]
        if plan:
            network, _ = plan
            channel_keys.append(network)
        channel_keys.extend(details.entity.genre_names)
        for channel_key in channel_keys:
            self.add_new_urls_to_channel(channel_key, [title.url])
        self.add_new_urls_to_channel(
            RECOMMENDATIONS_TOPIC,
            collection_urls(self._title_components(title.key)),
        )


# TODO: Validate


# TODO: Validate
class HuluImporterUpsert(HuluImporterChannels, ABC):
    # TODO: Validate
    def get_title_source(self, title_key: str) -> Source:
        """Get the source for the given title key.

        Seperate sources are used for titles that require additional subscription plans.
        """
        plan = title_plan(self._title_files(title_key)[0].details())
        source_key = "Hulu"
        if plan:
            network, is_subscription = plan
            if is_subscription:
                source_key = self._channel_name(network)

        if source_key not in self._sources:
            self._sources[source_key] = self.upsert_source(source_key)

        return self._sources[source_key]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        upserted_title = self._title_record(source, title_key).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(
            self._title_files(title_key)[0].details().entity.genre_names,
        )

        self._upsert_title_seasons(upserted_title)
        self._upsert_collection_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)
        self._set_title_update_at(upserted_title)

        return upserted_title

    # TODO: Validate
    def _upsert_collection_seasons(self, title: Title) -> None:
        for component in watch_components(self._title_components(title.key)):
            season_key = collection_season_key(title.key, component.id)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=component.name,
                season_number=0,
                sort_order=2147483647,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_collection_episodes(upserted_season, title.key)

    # TODO: Validate
    def _upsert_collection_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        for sort_order, item in enumerate(
            self._collection_items(season.key, title_key),
        ):
            episode_key = str(item.id)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            hero_artwork = item.artwork.video_horizontal_hero
            hero_path = hero_artwork.path if hero_artwork else None
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.name,
                description=item.description,
                url=episode_url(episode_key),
                image_url=image_url(hero_path),
                thumbnail_url=thumbnail_url(hero_path),
                duration=item.bundle.duration if item.bundle else None,
                air_date=item.premiere_date,
                episode_number=sort_order + 1,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)

    # TODO: Validate
    def _collection_season_keys(self, title_key: str) -> list[str]:
        return [
            collection_season_key(title_key, component.id)
            for component in watch_components(self._title_components(title_key))
        ]

    # TODO: Validate
    def _collection_items(
        self,
        season_key: str,
        title_key: str,
    ) -> list[SeriesCollectionItem | MovieCollectionItem]:
        _, component_id = split_collection_season_key(season_key)
        return list(
            watch_component(self._title_components(title_key), component_id).items,
        )

    # TODO: Validate
    def _collection_episode_keys(self, season_key: str, title_key: str) -> list[str]:
        return [str(item.id) for item in self._collection_items(season_key, title_key)]


# TODO: Validate
class HuluImporter(HuluImporterUpsert, ABC):
    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed_url = self.parse_url(url)
        if not (title := self._preload_title(parsed_url.title_key).one_or_none()):
            self._preload_and_download_files(parsed_url.title_key)
            title_source = self.get_title_source(parsed_url.title_key)
            title = self._upsert_title(title_source, parsed_url.title_key)
        return self._import_results(title, parsed_url)
