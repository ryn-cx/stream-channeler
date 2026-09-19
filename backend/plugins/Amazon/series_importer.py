from __future__ import annotations

from abc import ABC
from datetime import time
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from app.utils import tz_datetime
from plugins.Amazon.shared import AmazonImporter, AmazonShared
from plugins.utils.base_plugin.files import BaseFile
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Sequence


class AmazonSeriesFiles(AmazonShared, ABC):
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        # Detect changes to the season and new/deleted episodes.
        return [self.detail_file(season_key)]

    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [season.key for season in self.detail_file(title_key).parsed().seasons]

    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [
            episode.key
            for season_key in season_keys
            for episode in self.detail_file(season_key).parsed().episodes
        ]


class AmazonSeriesUpsert(AmazonSeriesFiles, AmazonImporter, ABC):
    @override
    def _upsert_title(self, source: Source, title_key: str) -> Title:
        detail_file = self.detail_file(title_key).parsed()
        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=detail_file.parent_title or detail_file.title,
            description=detail_file.synopsis,
            media_type=MediaType.series,
            url=detail_file.url,
            image_url=detail_file.image_url,
            thumbnail_url=detail_file.image_url,
            year=detail_file.release_year,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(detail_file.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)
        self.add_other_titles_on_page_to_channels(upserted_title)

        self._set_title_update_at(upserted_title)

        # Manage deleted series
        if not (
            detail_file.included_with_prime
            or detail_file.purchasable
            or detail_file.channels
        ):
            upserted_title.soft_delete()

        return upserted_title

    def _upsert_seasons(self, title: Title) -> None:
        seasons = self.detail_file(title.key).parsed().seasons
        for sort_order, season_entry in enumerate(seasons):
            season_key = season_entry.key
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=season_entry.name,
                season_number=season_entry.season_number,
                sort_order=sort_order,
                url=season_entry.url,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key)
            self._set_season_update_at(upserted_season)

            # Some seasons are listed on Amazon but not available to stream. These
            # entries are imported into the database so the information is available for
            # later updates.
            if self.detail_file(season_key).parsed().unavailable_message is not None:
                upserted_season.soft_delete()

    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        episodes = self.detail_file(season.key).parsed().episodes
        for sort_order, item in enumerate(episodes):
            existing_episode = Episode.get_from_memory(self.session, season, item.key)
            upserted_episode = Episode(
                key=item.key,
                watch_identifier=watch_identifier(self.plugin_name(), item.key),
                name=item.title,
                episode_number=item.episode_number,
                url=item.url,
                description=item.synopsis,
                image_url=item.image_url,
                thumbnail_url=item.image_url,
                duration=item.duration,
                # TODO: Is the None check needed?
                air_date=(
                    tz_datetime.combine(item.release_date, time.min)
                    if item.release_date
                    else None
                ),
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    item.key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)

            if not item.is_available:
                upserted_episode.soft_delete()


class AmazonSeriesImporter(AmazonSeriesUpsert):
    pass
