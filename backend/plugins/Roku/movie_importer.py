# TODO: Validate
"""Writing what The Roku Channel says about a movie into the database."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Roku.shared import (
    RokuImporter,
    RokuShared,
    build_season_key,
    split_season_key,
    title_url,
    video_url,
)
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class RokuMovieFiles(RokuShared, ABC):
    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.content_file(title_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [build_season_key(title_key, 0)]

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
class RokuMovieUpsert(RokuMovieFiles, RokuImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        return ParsedURL(self._url_content_key(url))

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        content = self._content(title_key)
        existing_title = Title.get_from_memory(self.session, source, title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=content.title,
            description=content.description,
            media_type=MediaType.movie,
            url=title_url(title_key),
            image_url=content.image_map.detail_background.path,
            thumbnail_url=content.image_map.detail_background.path,
            poster_url=content.image_map.detail_poster.path,
            poster_thumbnail_url=content.image_map.detail_poster.path,
            year=content.release_year,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(content.genres)

        self._upsert_season(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_season(self, title: Title) -> None:
        season_key = build_season_key(title.key, 0)
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
        content = self._content(title_key)
        Episode(
            key=title_key,
            watch_identifier=watch_identifier(self.plugin_name(), title_key),
            name=content.title,
            description=content.description,
            url=video_url(title_key),
            image_url=content.image_map.detail_poster.path,
            thumbnail_url=content.image_map.detail_poster.path,
            duration=content.run_time_seconds,
            episode_number=0,
            sort_order=0,
            air_date=content.release_date,
            data_timestamp=self._episode_files_data_timestamp(
                title_key,
                season.key,
                title_key,
            ),
            season_id=season.id,
        ).upsert(season, existing_episode)


# TODO: Validate
class RokuMovieImporter(RokuMovieUpsert):
    pass
