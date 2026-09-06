# TODO: Validate
"""Writing what HiDive says about a title into the database."""

from __future__ import annotations

import re
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season as SeasonModel
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.HiDive.constants import MOVIE_MEDIA_TYPE, SERIES_MEDIA_TYPE
from plugins.HiDive.shared import (
    MOVIE_URL_REGEX,
    SEASON_URL_REGEX,
    SERIES_URL_REGEX,
    HiDiveShared,
)
from plugins.HiDive.utils import (
    episode_number,
    episode_url,
    hero_image_url,
    movie_description,
    movie_duration,
    movie_title,
    release_date,
    season_bucket,
    season_hero,
    season_url,
    series_image_url,
    series_season_items,
    title_url,
    vod_hero,
)
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile

# TODO: Add support for individual episodes of a series.


# TODO: Validate
class HiDiveImporter(HiDiveShared, BaseImporter, ABC):
    pass


# TODO: Validate
class HiDiveSeries(HiDiveImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (SERIES_URL_REGEX, SEASON_URL_REGEX)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        domain_regex = self._domain_regex()
        if match := re.match(domain_regex + SERIES_URL_REGEX, url):
            title_key = match.group("series_key")
            self.raise_if_invalid_file(self.series_file(title_key), url)
            return MediaInfo(title_key)

        # HiDive's interface does not do a good job of seperating titles and seasons
        # and if a user uses a season URL it should be treated the same as a series
        # URL for a more intuitive user experience.
        if match := re.match(domain_regex + SEASON_URL_REGEX, url):
            season_key = match.group("season_key")
            season_file = self.season_file(season_key)
            self.raise_if_invalid_file(season_file, url)
            return MediaInfo(str(season_file.parsed().metadata.series.series_id))

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        series_file = self.series_file(title_key)
        series_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        return [
            TMDBLookupInfo(
                series_file.parsed().metadata.series.title,
                TMDBMediaType.tv,
                None,
            ),
        ]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.series_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # The season file detects new episodes and changes to the season.
        return [self.season_file(season_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The vod file detects changes to the episode information.
        return [self.vod_file(episode_key), self.season_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        series_data = self.series_file(title_key).parsed()
        return [str(item.id) for item in series_season_items(series_data)]

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
            bucket = season_bucket(self.season_file(season_key).parsed())
            episode_keys.extend(str(item.id) for item in bucket.attributes.items or [])
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
            series_data = self.series_file(title_key).parsed()
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=series_data.metadata.series.title,
                media_type=SERIES_MEDIA_TYPE,
                url=title_url(title_key),
                image_url=series_image_url(series_data),
                thumbnail_url=series_image_url(series_data),
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(None, data_timestamps)

        self._upsert_seasons(title, force=force)
        self._set_weekly_updates_from_episodes(title)
        self._soft_delete_missing(title_key)
        self.link_title_to_tmdb(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        series_data = self.series_file(title.key).parsed()
        for sort_order, season_info in enumerate(series_season_items(series_data)):
            season_key = str(season_info.id)
            hero = season_hero(self.season_file(season_key).parsed())

            season = SeasonModel.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                new_season = SeasonModel(
                    key=season_key,
                    name=season_info.title,
                    season_number=season_info.season_number,
                    sort_order=sort_order,
                    url=season_url(season_key),
                    image_url=hero_image_url(hero),
                    thumbnail_url=hero_image_url(hero),
                    data_timestamp=data_timestamps[0],
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episodes(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: SeasonModel,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        bucket = season_bucket(self.season_file(season.key).parsed())
        for sort_order, item in enumerate(bucket.attributes.items or []):
            episode_key = str(item.id)
            episode = Episode.get_from_memory(self.session, season, episode_key)
            if not self._episode_is_outdated(
                episode,
                season.key,
                title_key,
                force=force,
            ):
                continue

            hero = vod_hero(self.vod_file(episode_key).parsed())
            data_timestamps = self.episode_data_timestamps(
                episode_key,
                season.key,
                title_key,
            )
            new_episode = Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.title,
                episode_number=episode_number(item.title),
                url=episode_url(episode_key),
                description=item.description,
                image_url=item.thumbnail_url,
                thumbnail_url=item.thumbnail_url,
                duration=item.duration,
                sort_order=sort_order,
                air_date=release_date(hero),
                data_timestamp=data_timestamps[0],
                season_id=season.id,
            )
            episode = new_episode.upsert(season, episode)
            episode.set_update_at(None, data_timestamps)


# TODO: Validate
class HiDiveMovie(HiDiveImporter):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (MOVIE_URL_REGEX,)

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        if match := re.match(self._domain_regex() + MOVIE_URL_REGEX, url):
            title_key = match.group("movie_vod_key")
            self.raise_if_invalid_file(self.vod_file(title_key), url)
            return MediaInfo(title_key)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, title_key: str) -> list[TMDBLookupInfo]:
        vod_file = self.vod_file(title_key)
        vod_file.download_if_outdated(tz_datetime.now() - timedelta(days=7))
        hero = vod_hero(vod_file.parsed())
        premiere = release_date(hero)
        return [
            TMDBLookupInfo(
                movie_title(hero),
                TMDBMediaType.movie,
                premiere.year if premiere else None,
            ),
        ]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.vod_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.vod_file(season_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.vod_file(episode_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [title_key]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return list(season_keys)

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
            hero = vod_hero(self.vod_file(title_key).parsed())
            data_timestamps = self.title_data_timestamps(title_key)
            new_title = Title(
                key=title_key,
                name=movie_title(hero),
                description=movie_description(hero),
                url=title_url(title_key, MOVIE_MEDIA_TYPE),
                image_url=hero_image_url(hero),
                thumbnail_url=hero_image_url(hero),
                media_type=MOVIE_MEDIA_TYPE,
                data_timestamp=data_timestamps[0],
                source_id=source.id,
            )
            title = new_title.upsert(source, title)
            title.set_update_at(None, data_timestamps)

        self._upsert_seasons(title, force=force)
        self._soft_delete_missing(title_key)
        self.link_title_to_tmdb(title)

        return title

    # TODO: Validate
    def _upsert_seasons(self, title: Title, *, force: bool = False) -> None:
        for sort_order, season_key in enumerate(
            self._season_keys_from_title_files(title.key),
        ):
            hero = vod_hero(self.vod_file(title.key).parsed())

            season = SeasonModel.get_from_memory(self.session, title, season_key)
            if self._season_is_outdated(season, title.key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, title.key)
                new_season = SeasonModel(
                    key=season_key,
                    name=movie_title(hero),
                    season_number=0,
                    sort_order=sort_order,
                    url=title_url(title.key, MOVIE_MEDIA_TYPE),
                    image_url=hero_image_url(hero),
                    thumbnail_url=hero_image_url(hero),
                    data_timestamp=data_timestamps[0],
                    title_id=title.id,
                )
                season = new_season.upsert(title, season)
                season.set_update_at(None, data_timestamps)

            self._upsert_episode(season, title.key, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: SeasonModel,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, title_key)
        if not self._episode_is_outdated(
            episode,
            season.key,
            title_key,
            force=force,
        ):
            return

        hero = vod_hero(self.vod_file(title_key).parsed())
        data_timestamps = self.episode_data_timestamps(
            title_key,
            season.key,
            title_key,
        )
        new_episode = Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=movie_title(hero),
            description=movie_description(hero),
            url=episode_url(title_key),
            image_url=hero_image_url(hero),
            thumbnail_url=hero_image_url(hero),
            episode_number=0,
            sort_order=0,
            duration=movie_duration(hero),
            air_date=release_date(hero),
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )
        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
