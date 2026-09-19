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


class AmazonMovieFiles(AmazonShared, ABC):
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.detail_file(title_key)]

    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        # Movies have the same title and season key
        return [title_key]

    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        # Movies have the same title, season, and episode key
        return season_keys


class AmazonMovieUpsert(AmazonMovieFiles, AmazonImporter, ABC):
    @override
    def _upsert_title(self, source: Source, title_key: str) -> Title:
        detail_file = self.detail_file(title_key).parsed()
        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=detail_file.title,
            description=detail_file.synopsis,
            media_type=MediaType.movie,
            url=detail_file.url,
            image_url=detail_file.image_url,
            thumbnail_url=detail_file.image_url,
            year=detail_file.release_year,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(detail_file.genres)

        self._upsert_season(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)
        self.add_other_titles_on_page_to_channels(upserted_title)

        self._set_title_update_at(upserted_title)

        # Manage deleted movies
        if detail_file.unavailable_message is not None:
            upserted_title.soft_delete()

        return upserted_title

    def _upsert_season(self, title: Title) -> None:
        existing_season = Season.get_from_memory(self.session, title, title.key)
        upserted_season = Season(
            key=title.key,
            season_number=0,
            sort_order=0,
            data_timestamp=self._season_files_data_timestamp(title.key, title.key),
            title_id=title.id,
        ).upsert(title, existing_season)

        self._upsert_episode(upserted_season, title.key)
        self._set_season_update_at(upserted_season)

    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        existing_episode = Episode.get_from_memory(self.session, season, title_key)
        parsed = self.detail_file(title_key).parsed()
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=parsed.title,
            description=parsed.synopsis,
            url=parsed.url,
            image_url=parsed.image_url,
            thumbnail_url=parsed.image_url,
            duration=parsed.duration,
            episode_number=0,
            sort_order=0,
            # TODO: Is the None check needed?
            air_date=(
                tz_datetime.combine(parsed.release_date, time.min)
                if parsed.release_date
                else None
            ),
            data_timestamp=self._episode_files_data_timestamp(
                title_key,
                season.key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)


class AmazonMovieImporter(AmazonMovieUpsert):
    pass
