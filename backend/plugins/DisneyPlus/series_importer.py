# TODO: Validate
"""Writing what Disney+ says about a series into the database."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.DisneyPlus.files import SeasonEntity
from plugins.DisneyPlus.shared import DisneyPlusImporter
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from kneeminus.entity.models import EntityModel
    from kneeminus.entity.models import Episode as EntityEpisode
    from kneeminus.entity.models import Season as EntitySeason

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class DisneyPlusSeriesFiles(DisneyPlusImporter, ABC):
    # TODO: Validate
    def season_file(self, entity_id: str, season_id: str) -> SeasonEntity:
        return self._cached_file(SeasonEntity, entity_id, season_id)

    # TODO: Validate
    @staticmethod
    def seasons(entity: EntityModel) -> list[EntitySeason]:
        return entity.seasons

    # TODO: Validate
    @staticmethod
    def season_episodes(
        season_entity: EntityModel,
        season_id: str,
    ) -> list[EntityEpisode]:
        for season in season_entity.seasons:
            if str(season.season_id) == season_id:
                return season.episodes
        return []

    # TODO: Validate
    def _seasons(self, title_key: str) -> list[EntitySeason]:
        return self.seasons(self._entity(title_key))

    # TODO: Validate
    def _season_episodes(self, title_key: str, season_id: str) -> list[EntityEpisode]:
        return self.season_episodes(
            self.season_file(title_key, season_id).parsed(),
            season_id,
        )

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_id = self.split_season_key(season_key)
        return [self.season_file(title_key, season_id)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # The episode list comes down with the season's page, so the page is what
        # says whether an episode read out of it has changed.
        return self._season_files(season_key, title_key)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            self.build_season_key(title_key, str(season.season_id))
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
            _title_key, season_id = self.split_season_key(season_key)
            episode_keys += [
                str(episode.episode_id)
                for episode in self._season_episodes(title_key, season_id)
            ]
        return episode_keys


# TODO: Validate
class DisneyPlusSeriesUpsert(DisneyPlusSeriesFiles, ABC):
    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        entity = self._entity(title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=self.required_value(entity.title, "title"),
            description=entity.summary,
            media_type=MediaType.series,
            url=self.title_url(title_key),
            image_url=self._background_image_url(title_key),
            thumbnail_url=self._background_thumbnail_url(title_key),
            year=entity.release_year,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(entity.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, season_entry in enumerate(self._seasons(title.key)):
            season_id = str(season_entry.season_id)
            season_key = self.build_season_key(title.key, season_id)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                name=season_entry.name,
                season_number=season_entry.season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key, season_id)
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_id: str,
    ) -> None:
        for sort_order, item in enumerate(self._season_episodes(title_key, season_id)):
            episode_key = str(item.episode_id)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.name,
                episode_number=item.episode_number,
                url=self.video_url(episode_key),
                description=item.summary,
                image_url=item.image.url,
                thumbnail_url=item.image.thumbnail_url,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate


# TODO: Validate
class DisneyPlusSeriesImporter(DisneyPlusSeriesUpsert):
    pass
