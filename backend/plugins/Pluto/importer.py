# TODO: Validate
"""Writing what Pluto TV says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Pluto.constants import (
    MILLISECONDS_PER_SECOND,
    MOVIE_URL_REGEX,
    SERIES_URL_REGEX,
)
from plugins.Pluto.shared import PlutoShared
from plugins.Pluto.utils import (
    build_season_key,
    episode_url,
    movie_season_key,
    movie_url,
    poster_url,
    season_episodes,
    season_url,
    seasons,
    series_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from notaplanet.items.models import ItemsModelItem
    from notaplanet.seasons.models import Episode as SeriesEpisode
    from notaplanet.seasons.models import Season as SeriesSeason
    from notaplanet.seasons.models import SeasonsModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class PlutoImporter(PlutoShared, BaseImporter, ABC):
    pass


# TODO: Validate
class PlutoSeriesImporter(PlutoImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + SERIES_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.seasons_file(title_key), url)
            return ParsedURL(title_key, episode_key=match.group("episode_key"))

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _series(self, title_key: str) -> SeasonsModel:
        return self.seasons_file(title_key).parsed()

    # TODO: Validate
    def _seasons(self, title_key: str) -> list[SeriesSeason]:
        return seasons(self._series(title_key))

    # TODO: Validate
    def _season_episodes(
        self,
        title_key: str,
        season_number: int,
    ) -> list[SeriesEpisode]:
        return season_episodes(self._series(title_key), season_number)

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons of it.
        return [self.seasons_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # The seasons and their episodes all come down with the title's own file.
        return [self.seasons_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.seasons_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            build_season_key(title_key, season.number)
            for season in self._seasons(title_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            _title_key, season_number = split_season_key(season_key)
            episode_keys += [
                episode.field_id
                for episode in self._season_episodes(title_key, season_number)
            ]
        return episode_keys

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        series = self._series(title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=series.name,
            description=series.description,
            media_type=MediaType.series,
            url=series_url(title_key),
            image_url=series.featured_image.path,
            thumbnail_url=series.featured_image.path,
            poster_url=poster_url(series.covers),
            poster_thumbnail_url=poster_url(series.covers),
            data_timestamp=data_timestamp,
            source_id=source.id,
            update_at=data_timestamp + timedelta(days=7),
        ).upsert(source, existing_title)
        upserted_title.upsert_genres([series.genre])

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, series_season in enumerate(self._seasons(title.key)):
            season_number = series_season.number
            season_key = build_season_key(title.key, season_number)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                season_number=season_number,
                sort_order=sort_order,
                url=season_url(title.key, season_number),
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(
                upserted_season,
                title.key,
                season_number,
            )
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_number: int,
    ) -> None:
        for sort_order, series_episode in enumerate(
            self._season_episodes(title_key, season_number),
        ):
            episode_key = series_episode.field_id
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=series_episode.name,
                description=series_episode.description,
                episode_number=series_episode.number,
                url=episode_url(title_key, season_number, episode_key),
                image_url=series_episode.poster16_9.path,
                thumbnail_url=series_episode.poster16_9.path,
                duration=(
                    series_episode.original_content_duration // MILLISECONDS_PER_SECOND
                ),
                air_date=series_episode.clip.original_release_date,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class PlutoMovieImporter(PlutoImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        if match := re.match(self._domains_regex() + MOVIE_URL_REGEX, url):
            title_key = match.group("title_key")
            self.raise_invalid_url_if_no_content(self.items_file(title_key), url)
            return ParsedURL(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _item(self, title_key: str) -> ItemsModelItem:
        return self.items_file(title_key).parsed().root[0]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.items_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.items_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.items_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [movie_season_key(title_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [split_season_key(season_key)[0] for season_key in season_keys]

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        item = self._item(title_key)
        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=item.name,
            description=item.description,
            media_type=MediaType.movie,
            url=movie_url(title_key),
            image_url=item.featured_image.path,
            thumbnail_url=item.featured_image.path,
            poster_url=poster_url(item.covers),
            poster_thumbnail_url=poster_url(item.covers),
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres([item.genre])

        self._upsert_season(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(self, title: Title) -> None:
        season_key = movie_season_key(title.key)
        existing_season = Season.get_from_memory(self.session, title, season_key)
        upserted_season = Season(
            key=season_key,
            season_number=0,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(season_key, title.key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episode(upserted_season, title.key)
        self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        existing_episode = Episode.get_from_memory(self.session, season, title_key)
        item = self._item(title_key)
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=item.name,
            description=item.description,
            episode_number=0,
            url=movie_url(title_key),
            image_url=item.featured_image.path,
            thumbnail_url=item.featured_image.path,
            duration=(item.original_content_duration // MILLISECONDS_PER_SECOND),
            sort_order=0,
            data_timestamp=self._episode_files_data_timestamp(
                title_key,
                season.key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)
