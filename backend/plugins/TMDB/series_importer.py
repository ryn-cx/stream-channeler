# TODO: Validate
"""Writing what TMDB says about a series into the database."""

from __future__ import annotations

import re
import uuid
from abc import ABC
from collections.abc import Sequence
from datetime import datetime
from random import Random
from typing import Any, override

from sqlmodel import col, select
from tminidb.tv_season.details.models import TvSeasonDetailsModel

from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.models import (
    TmdbEpisodeOrder,
    TmdbEpisodeOrderEntry,
    TmdbEpisodeOrderGroup,
)
from app.tmdb_media.tmdb import (
    get_media_type_and_season_id,
    get_media_type_and_tmdb_id,
    tmdb_episode_key,
    tmdb_season_key,
    tmdb_title_key,
)
from app.utils import tz_datetime
from plugins.TMDB.constants import TV_URL_REGEX
from plugins.TMDB.files import (
    TVEpisodeGroupsDetails,
    TVSeasonsDetails,
    TVSeasonsWatchProviders,
    TVSeriesEpisodeGroups,
    TVSeriesImages,
)
from plugins.TMDB.imdb_importer import TMDBIMDbImporter
from plugins.TMDB.shared import TMDBImporter
from plugins.TMDB.videos_importer import TMDBVideosImporter
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.update_at import set_air_date_update_at
from plugins.utils.base_plugin.url import ParsedURL


# TODO: Validate
class TMDBSeriesFiles(TMDBVideosImporter, TMDBIMDbImporter, ABC):
    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (TV_URL_REGEX,)

    # TODO: Validate
    def tv_series_episode_groups_file(
        self,
        tmdb_tv_title_id: int,
    ) -> TVSeriesEpisodeGroups:
        return self._cached_file(TVSeriesEpisodeGroups, tmdb_tv_title_id)

    # TODO: Validate
    def tv_episode_groups_details_file(
        self,
        group_id: str,
    ) -> TVEpisodeGroupsDetails:
        return self._cached_file(TVEpisodeGroupsDetails, group_id)

    # TODO: Validate
    def tv_series_images_file(self, tmdb_tv_title_id: int) -> TVSeriesImages:
        return self._cached_file(TVSeriesImages, tmdb_tv_title_id)

    # TODO: Validate
    def tv_seasons_details_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsDetails:
        return self._cached_file(TVSeasonsDetails, tmdb_tv_title_id, season_number)

    # TODO: Validate
    def tv_seasons_watch_providers_file(
        self,
        tmdb_tv_title_id: int,
        season_number: int,
    ) -> TVSeasonsWatchProviders:
        return self._cached_file(
            TVSeasonsWatchProviders,
            tmdb_tv_title_id,
            season_number,
        )

    # TODO: Validate
    def seasons(self, title_key: str) -> list[TvSeasonDetailsModel]:
        """Return the seasons for the title, which are the ones TVSeriesDetails holds.

        An episode order TMDB publishes is recorded against the title rather than read
        in, so the seasons never depend on which order anything is being read in.
        """
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        return [
            self.tv_seasons_details_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=season.season_number,
            ).parsed()
            for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons
        ]

    # TODO: Validate
    def _native_season_number(self, season_key: str, title_key: str) -> int:
        """Return the number TMDB's own seasons give the season `season_key` names."""
        _, tmdb_tv_season_id = get_media_type_and_season_id(season_key)
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons:
            if season.id == tmdb_tv_season_id:
                return season.season_number
        message = f"{title_key} has no season {season_key}"
        raise ValueError(message)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        return [
            tmdb_season_key(TMDBMediaType.tv, season.id)
            for season in self.tv_series_details_file(tmdb_tv_title_id).parsed().seasons
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

        wanted = set(season_keys)
        return [
            tmdb_episode_key(TMDBMediaType.tv, episode.id)
            for season in self.seasons(title_key)
            if tmdb_season_key(TMDBMediaType.tv, season.id) in wanted
            for episode in season.episodes
        ]

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        return [
            *self._listing_title_files(tmdb_tv_title_id),
            *self._episode_group_files(tmdb_tv_title_id),
            *self._fallback_backdrop_files(title_key, tmdb_tv_title_id),
        ]

    # TODO: Validate
    def _listing_title_files(self, tmdb_tv_title_id: int) -> list[BaseFile[Any]]:
        return [
            self.tv_series_details_file(tmdb_tv_title_id),
            self.tv_series_episode_groups_file(tmdb_tv_title_id),
            self.tv_series_watch_providers_file(tmdb_tv_title_id),
            self.tv_series_keywords_file(tmdb_tv_title_id),
            self.tv_series_videos_file(tmdb_tv_title_id),
        ]

    # TODO: Validate
    def _episode_group_files(self, tmdb_tv_title_id: int) -> list[BaseFile[Any]]:
        groups_file = self.tv_series_episode_groups_file(tmdb_tv_title_id)
        return [
            self.tv_episode_groups_details_file(option.id)
            for option in groups_file.parsed().results
        ]

    # TODO: Validate
    @override
    def _preload_and_download_title_files(
        self,
        title_key: str,
        update_at: datetime | None,
    ) -> None:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        listing_files = self._listing_title_files(tmdb_tv_title_id)
        self._preload_files(listing_files)
        self._download_if_outdated(listing_files, update_at)
        group_files = self._episode_group_files(tmdb_tv_title_id)
        self._preload_files(group_files)
        self._download_if_outdated(group_files, update_at)

    # TODO: Validate
    def _fallback_backdrop_files(
        self,
        title_key: str,
        tmdb_tv_title_id: int,
    ) -> Sequence[BaseFile[Any]]:
        for season in self.seasons(title_key):
            if any(not episode.still_path for episode in season.episodes):
                return [self.tv_series_images_file(tmdb_tv_title_id)]
        return []

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        season_number = self._native_season_number(season_key, title_key)
        return [
            self.tv_seasons_details_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=season_number,
            ),
            self.tv_seasons_watch_providers_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=season_number,
            ),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        return [
            self.tv_seasons_details_file(
                tmdb_tv_title_id=tmdb_tv_title_id,
                season_number=self._native_season_number(season_key, title_key),
            ),
        ]


# TODO: Validate
class TMDBSeriesUpsert(TMDBSeriesFiles, TMDBImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        regex_match = re.match(self._domains_regex() + TV_URL_REGEX, url)
        if regex_match is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        tmdb_tv_title_id = int(regex_match.group("title_key"))
        self.raise_invalid_url_if_no_content(
            self.tv_series_details_file(tmdb_tv_title_id),
            url,
        )
        return ParsedURL(tmdb_title_key(TMDBMediaType.tv, tmdb_tv_title_id))

    # TODO: Validate

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        existing_title = Title.get_from_memory(self.session, source, title_key)
        series = self.tv_series_details_file(tmdb_tv_title_id).parsed()
        upserted_title = Title(
            key=title_key,
            name=series.name,
            description=series.overview,
            url=self.tmdb_url(TMDBMediaType.tv, tmdb_tv_title_id),
            image_url=self.image_url(series.backdrop_path or series.poster_path),
            thumbnail_url=self.thumbnail_url(
                series.backdrop_path or series.poster_path,
            ),
            poster_url=self.image_url(series.poster_path),
            poster_thumbnail_url=self.thumbnail_url(series.poster_path),
            year=self.parse_release_year(series.first_air_date),
            tmdb_score=series.vote_average,
            tmdb_popularity=series.popularity,
            original_language=series.original_language,
            media_type=MediaType.series,
            extra=existing_title.extra if existing_title else {},
            data_timestamp=self._title_files_data_timestamp(title_key),
            tmdb_title_validated_at=tz_datetime.now(),
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(genre.name for genre in series.genres)
        upserted_title.set_spoken_languages(
            {
                language.iso_639_1: language.english_name
                for language in series.spoken_languages
            },
        )

        self._upsert_seasons(upserted_title, title_key, tmdb_tv_title_id)
        self._upsert_episode_orders(upserted_title, tmdb_tv_title_id)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self._set_title_update_at(upserted_title)
        self._upsert_imdb_score(upserted_title)
        if series.next_episode_to_air:
            next_air_date = self.clean_air_datetime(series.next_episode_to_air.air_date)
            if next_air_date:
                set_air_date_update_at(upserted_title, [next_air_date])
        self._set_linked_titles_update_at(upserted_title)
        self.record_providers(
            upserted_title,
            self.tv_series_watch_providers_file(tmdb_tv_title_id).parsed(),
        )
        self._upsert_videos_title(upserted_title)
        return upserted_title

    # TODO: Validate
    @override
    def _preload_and_download_files(self, title: Title | str) -> None:
        super()._preload_and_download_files(title)
        if isinstance(title, str):
            self._download_fallback_backdrops(title, None)
        else:
            self._download_fallback_backdrops(title.key, title.update_at)

    # TODO: Validate
    def _download_fallback_backdrops(
        self,
        title_key: str,
        update_at: datetime | None,
    ) -> None:
        _, tmdb_tv_title_id = get_media_type_and_tmdb_id(title_key)
        self._download_if_outdated(
            self._fallback_backdrop_files(title_key, tmdb_tv_title_id),
            update_at,
        )

    # TODO: Validate
    def _upsert_seasons(
        self,
        title: Title,
        title_key: str,
        tmdb_tv_title_id: int,
    ) -> None:
        for source in self.seasons(title_key):
            season_key = tmdb_season_key(TMDBMediaType.tv, source.id)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=source.name,
                season_number=source.season_number,
                sort_order=source.season_number,
                image_url=self.image_url(source.poster_path),
                thumbnail_url=self.thumbnail_url(source.poster_path),
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title_key,
                ),
                title_id=title.id,
                update_at=None,
            ).upsert(title, existing_season)
            self._upsert_episodes(
                season=upserted_season,
                source=source,
                title_key=title_key,
                tmdb_tv_title_id=tmdb_tv_title_id,
            )
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        source: TvSeasonDetailsModel,
        title_key: str,
        tmdb_tv_title_id: int,
    ) -> None:
        season_key = season.key
        for sort_order, episode_source in enumerate(source.episodes):
            key = tmdb_episode_key(TMDBMediaType.tv, episode_source.id)
            existing_episode = Episode.get_from_memory(self.session, season, key)
            still_path = episode_source.still_path or self._fallback_backdrop_path(
                tmdb_tv_title_id=tmdb_tv_title_id,
                tmdb_tv_episode_id=episode_source.id,
            )
            Episode(
                key=key,
                watch_identifier=key,
                name=episode_source.name,
                description=episode_source.overview,
                url=self.tmdb_url(TMDBMediaType.tv, tmdb_tv_title_id),
                image_url=self.image_url(still_path),
                thumbnail_url=self.thumbnail_url(still_path),
                duration=self.runtime_in_seconds(episode_source.runtime),
                air_date=self.clean_air_datetime(episode_source.air_date),
                episode_number=episode_source.episode_number,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    key,
                    season_key,
                    title_key,
                ),
                season_id=season.id,
                update_at=None,
            ).upsert(season, existing_episode)

    # TODO: Validate
    def _upsert_episode_orders(self, title: Title, tmdb_tv_title_id: int) -> None:
        groups_file = self.tv_series_episode_groups_file(tmdb_tv_title_id)
        if not groups_file.record_content:
            return
        episodes_by_key = {
            episode.key: episode
            for season in title.children
            for episode in season.children
        }
        existing_orders = {
            order.tmdb_group_id: order
            for order in self.session.exec(
                select(TmdbEpisodeOrder).where(
                    col(TmdbEpisodeOrder.tmdb_title_id) == title.id,
                ),
            ).all()
        }
        for option in groups_file.parsed().results:
            order = existing_orders.get(option.id)
            if order is None:
                order = TmdbEpisodeOrder(
                    tmdb_title_id=title.id,
                    tmdb_group_id=option.id,
                )
                self.session.add(order)
            order.name = option.name
            order.description = option.description
            order.type = option.type
            order.group_count = option.group_count
            order.episode_count = option.episode_count
            self._upsert_episode_order_entries(
                order,
                option.id,
                episodes_by_key,
                is_new=existing_orders.get(option.id) is None,
            )

    # TODO: Validate
    def _upsert_episode_order_entries(
        self,
        order: TmdbEpisodeOrder,
        group_id: str,
        episodes_by_key: dict[str, Episode],
        *,
        is_new: bool,
    ) -> None:
        existing_entries = (
            {}
            if is_new
            else {
                entry.tmdb_episode_id: entry
                for group in order.groups
                for entry in group.entries
            }
        )
        existing_groups = (
            {} if is_new else {group.group_index: group for group in order.groups}
        )
        placed: set[uuid.UUID] = set()
        placed_groups: set[int] = set()
        groups = self.tv_episode_groups_details_file(group_id).parsed().groups
        for group_index, source_group in enumerate(groups):
            placed_groups.add(group_index)
            group = existing_groups.get(group_index)
            if group is None:
                group = TmdbEpisodeOrderGroup(
                    order_id=order.id,
                    group_index=group_index,
                )
                self.session.add(group)
            group.name = source_group.name
            for sort_order, episode_source in enumerate(source_group.episodes):
                key = tmdb_episode_key(TMDBMediaType.tv, episode_source.id)
                episode = episodes_by_key.get(key)
                if episode is None or episode.id in placed:
                    continue
                placed.add(episode.id)
                entry = existing_entries.get(episode.id)
                if entry is None:
                    entry = TmdbEpisodeOrderEntry(
                        order_id=order.id,
                        tmdb_episode_id=episode.id,
                    )
                    self.session.add(entry)
                entry.group_id = group.id
                entry.episode_number = sort_order + 1
                entry.sort_order = sort_order
        for episode_id, entry in existing_entries.items():
            if episode_id not in placed:
                self.session.delete(entry)
        for group_index, group in existing_groups.items():
            if group_index not in placed_groups:
                self.session.delete(group)

    # TODO: Validate
    def _title_backdrop_paths(self, tmdb_tv_title_id: int) -> list[str]:
        cached: dict[int, list[str]] = self.session.info.setdefault(
            "tmdb_title_backdrop_paths",
            {},
        )
        if tmdb_tv_title_id not in cached:
            images = self.tv_series_images_file(tmdb_tv_title_id).parsed()
            cached[tmdb_tv_title_id] = [
                backdrop.file_path for backdrop in images.backdrops
            ]
        return cached[tmdb_tv_title_id]

    # TODO: Validate
    def _fallback_backdrop_path(
        self,
        tmdb_tv_title_id: int,
        tmdb_tv_episode_id: int,
    ) -> str | None:
        backdrop_paths = self._title_backdrop_paths(tmdb_tv_title_id)
        if not backdrop_paths:
            return None
        return Random(tmdb_tv_episode_id).choice(backdrop_paths)  # noqa: S311


# TODO: Validate
class TMDBSeries(TMDBSeriesUpsert):
    pass
