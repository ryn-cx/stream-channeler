# TODO: Validate
"""Writing what Pluto TV says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.titles.models import Title
from app.utils.update_at import staggered_monthly_update_at
from plugins.Pluto.constants import MILLISECONDS_PER_SECOND
from plugins.Pluto.shared import MOVIE_URL_REGEX, SERIES_URL_REGEX, PlutoShared
from plugins.Pluto.utils import (
    build_season_key,
    episode_url,
    movie_season_key,
    movie_url,
    season_episodes,
    season_url,
    seasons,
    series_url,
    split_season_key,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import URLTitleInfo

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
class PlutoSeries(PlutoImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        if match := re.match(self._domain_regex() + SERIES_URL_REGEX, url):
            title_key = match.group("series_key")
            self.raise_if_invalid_file(self.seasons_file(title_key), url)
            return URLTitleInfo(title_key, episode_key=match.group("episode_key"))

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _series(self, title_key: str) -> SeasonsModel:
        return self.seasons_file(title_key).parsed()

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        return [TMDBLookupInfo(self._series(title_key).name, TMDBMediaType.tv, None)]

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
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            series = self._series(title_key)
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=series.name,
                description=series.description,
                media_type="Series",
                url=series_url(title_key),
                image_url=series.featured_image.path,
                thumbnail_url=series.featured_image.path,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(min(data_timestamps) + timedelta(days=7), data_timestamps)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, series_season in enumerate(self._seasons(title.key)):
            season_number = series_season.number
            season_key = build_season_key(title.key, season_number)
            season = Season.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                new_season = Season(
                    key=season_key,
                    season_number=season_number,
                    sort_order=sort_order,
                    url=season_url(title.key, season_number),
                    data_timestamp=max(data_timestamps),
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(
                season,
                title.key,
                season_number,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, series_episode in enumerate(
            self._season_episodes(title_key, season_number),
        ):
            episode_key = series_episode.field_id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                title_key,
            )
            new_episode = Episode(
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
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class PlutoMovie(PlutoImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        if match := re.match(self._domain_regex() + MOVIE_URL_REGEX, url):
            title_key = match.group("movie_key")
            self.raise_if_invalid_file(self.items_file(title_key), url)
            return URLTitleInfo(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _item(self, title_key: str) -> ItemsModelItem:
        return self.items_file(title_key).parsed().root[0]

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        return [TMDBLookupInfo(self._item(title_key).name, TMDBMediaType.movie, None)]

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
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        item = self._item(title_key)
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=item.name,
                description=item.description,
                media_type="Movie",
                url=movie_url(title_key),
                image_url=item.featured_image.path,
                thumbnail_url=item.featured_image.path,
                data_timestamp=max(data_timestamps),
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(
                staggered_monthly_update_at(title_key, min(data_timestamps)),
                data_timestamps,
            )

        self._upsert_season(title, force=force)
        self._soft_delete_missing(title_key)

        return title

    # TODO: Validate
    def _upsert_season(self, title: Title, *, force: bool = False) -> None:
        season_key = movie_season_key(title.key)
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title.key, force=force):
            data_timestamps = self.season_data_timestamps(season_key, title.key)
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            )
            season = new_season.upsert(title, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episode(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if self._episode_is_outdated(episode, season.key, title_key, force=force):
            item = self._item(title_key)
            data_timestamps = self.episode_data_timestamps(
                title_key,
                season.key,
                title_key,
            )
            new_episode = Episode(
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
                data_timestamp=max(data_timestamps),
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
