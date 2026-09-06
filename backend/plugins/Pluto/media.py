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
from app.shows.models import Show
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
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from notaplanet.items.models import ItemsModelItem
    from notaplanet.seasons.models import Episode as SeriesEpisode
    from notaplanet.seasons.models import Season as SeriesSeason
    from notaplanet.seasons.models import SeasonsModel

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class PlutoMedia(PlutoShared, BaseImporter, ABC):
    pass


# TODO: Validate
class PlutoSeries(PlutoMedia):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + SERIES_URL_REGEX, url):
            show_key = match.group("series_key")
            self.raise_if_invalid_file(self.seasons_file(show_key), url)
            return MediaInfo(show_key, episode_key=match.group("episode_key"))

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _series(self, show_key: str) -> SeasonsModel:
        return self.seasons_file(show_key).parsed()

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return [TMDBLookupInfo(self._series(show_key).name, TMDBMediaType.tv, None)]

    # TODO: Validate
    def _seasons(self, show_key: str) -> list[SeriesSeason]:
        return seasons(self._series(show_key))

    # TODO: Validate
    def _season_episodes(
        self,
        show_key: str,
        season_number: int,
    ) -> list[SeriesEpisode]:
        return season_episodes(self._series(show_key), season_number)

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the show and new seasons of it.
        return [self.seasons_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        # The seasons and their episodes all come down with the show's own file.
        return [self.seasons_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.seasons_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            build_season_key(show_key, season.number)
            for season in self._seasons(show_key)
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            _show_key, season_number = split_season_key(season_key)
            episode_keys += [
                episode.field_id
                for episode in self._season_episodes(show_key, season_number)
            ]
        return episode_keys

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            series = self._series(show_key)
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=series.name,
                description=series.description,
                media_type="Series",
                url=series_url(show_key),
                image_url=series.featured_image.path,
                thumbnail_url=series.featured_image.path,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(days=7), data_timestamps)

        self._upsert_seasons(show, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons(self, show: Show, *, force: bool = False) -> None:
        for sort_order, series_season in enumerate(self._seasons(show.key)):
            season_number = series_season.number
            season_key = build_season_key(show.key, season_number)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show.key)
                new_season = Season(
                    key=season_key,
                    season_number=season_number,
                    sort_order=sort_order,
                    url=season_url(show.key, season_number),
                    data_timestamp=data_timestamps[0],
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(
                season,
                show.key,
                season_number,
                force=force,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        season_number: int,
        *,
        force: bool = False,
    ) -> None:
        for sort_order, series_episode in enumerate(
            self._season_episodes(show_key, season_number),
        ):
            episode_key = series_episode.field_id
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                show_key,
                force=force,
            ):
                continue

            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=series_episode.name,
                description=series_episode.description,
                episode_number=series_episode.number,
                url=episode_url(show_key, season_number, episode_key),
                image_url=series_episode.poster16_9.path,
                thumbnail_url=series_episode.poster16_9.path,
                duration=(
                    series_episode.original_content_duration // MILLISECONDS_PER_SECOND
                ),
                air_date=series_episode.clip.original_release_date,
                sort_order=sort_order,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class PlutoMovie(PlutoMedia):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + MOVIE_URL_REGEX, url):
            show_key = match.group("movie_key")
            self.raise_if_invalid_file(self.items_file(show_key), url)
            return MediaInfo(show_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _item(self, show_key: str) -> ItemsModelItem:
        return self.items_file(show_key).parsed().root[0]

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        return [TMDBLookupInfo(self._item(show_key).name, TMDBMediaType.movie, None)]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.items_file(show_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.items_file(show_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.items_file(show_key)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [movie_season_key(show_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [split_season_key(season_key)[0] for season_key in season_keys]

    # TODO: Validate
    @override
    def upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        item = self._item(show_key)
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=item.name,
                description=item.description,
                media_type="Movie",
                url=movie_url(show_key),
                image_url=item.featured_image.path,
                thumbnail_url=item.featured_image.path,
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(
                staggered_monthly_update_at(show_key, data_timestamp),
                data_timestamps,
            )

        self._upsert_season(show, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season(self, show: Show, *, force: bool = False) -> None:
        season_key = movie_season_key(show.key)
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show.key, force=force):
            data_timestamps = self.season_data_timestamps(season_key, show.key)
            new_season = Season(
                key=season_key,
                season_number=0,
                sort_order=0,
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(None, data_timestamps)

        self._upsert_episode(season, show.key, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, show_key)
        if self._episode_is_outdated(episode, season.key, show_key, force=force):
            item = self._item(show_key)
            data_timestamps = self.episode_data_timestamps(
                show_key,
                season.key,
                show_key,
            )
            new_episode = Episode(
                key=show_key,
                watch_identifier=watch_identifier(self.plugin_name(), show_key),
                name=item.name,
                description=item.description,
                episode_number=0,
                url=movie_url(show_key),
                image_url=item.featured_image.path,
                thumbnail_url=item.featured_image.path,
                duration=(item.original_content_duration // MILLISECONDS_PER_SECOND),
                sort_order=0,
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)
