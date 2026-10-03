# TODO: Validate
"""Writing what The Roku Channel says about a series into the database."""

from __future__ import annotations

from abc import ABC
from typing import TYPE_CHECKING, Any, override
from uuid import UUID

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Roku.files import SeasonEpisodesFile
from plugins.Roku.shared import RokuImporter
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nana.content.models import ContentModel
    from nana.content.models import Episode as ContentEpisode
    from nana.content.models import Episode2 as SeasonEpisode

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class RokuSeriesFiles(RokuImporter, ABC):
    # TODO: Validate
    def season_episodes_file(self, episode_key: str) -> SeasonEpisodesFile:
        return self._cached_file(SeasonEpisodesFile, episode_key)

    # TODO: Validate
    @staticmethod
    def content_id(value: str | UUID) -> str:
        """Return a Roku content id as the 32 character string the API uses."""
        return value.hex if isinstance(value, UUID) else value

    # TODO: Validate
    @staticmethod
    def title_episodes(content: ContentModel) -> list[ContentEpisode]:
        return content.episodes or []

    # TODO: Validate
    @classmethod
    def season_numbers(cls, content: ContentModel) -> list[int]:
        numbers: list[int] = []
        for episode in cls.title_episodes(content):
            season_number = int(episode.season_number)
            if season_number not in numbers:
                numbers.append(season_number)
        return numbers

    # TODO: Validate
    @classmethod
    def first_episode_key(cls, content: ContentModel, season_number: int) -> str:
        for episode in cls.title_episodes(content):
            if int(episode.season_number) == season_number:
                return cls.content_id(episode.meta.id)
        msg = f"No episodes for season {season_number}."
        raise ValueError(msg)

    # TODO: Validate
    @staticmethod
    def season_episodes(season_content: ContentModel) -> list[SeasonEpisode]:
        season = season_content.season
        if season is None:
            return []
        return season.episodes

    # TODO: Validate
    def _season_episodes(
        self,
        title_key: str,
        season_number: int,
    ) -> list[SeasonEpisode]:
        episode_key = self.first_episode_key(self._content(title_key), season_number)
        return self.season_episodes(self.season_episodes_file(episode_key).parsed())

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_number = self.split_season_key(season_key)
        episode_key = self.first_episode_key(self._content(title_key), season_number)
        return [self.season_episodes_file(episode_key)]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return self._season_files(season_key, title_key)

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return [
            self.build_season_key(title_key, season_number)
            for season_number in self.season_numbers(self._content(title_key))
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
            _title_key, season_number = self.split_season_key(season_key)
            episode_keys += [
                self.content_id(episode.meta.id)
                for episode in self._season_episodes(title_key, season_number)
            ]
        return episode_keys


# TODO: Validate
class RokuSeriesUpsert(RokuSeriesFiles, RokuImporter, ABC):
    # TODO: Validate
    @override
    def parse_url(self, url: str) -> ParsedURL:
        key = self._url_content_key(url)
        series = self._content(key).series
        if series is None:
            return ParsedURL(key)

        # A season has its number after its id, an episode does not, and only
        # an episode is a title of its own to point at.
        title_key = self.content_id(series.meta.id)
        if "-" in key:
            return ParsedURL(title_key)
        return ParsedURL(title_key, episode_key=key)

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        content = self._content(title_key)
        data_timestamp = self._title_files_data_timestamp(title_key)
        upserted_title = Title(
            key=title_key,
            name=content.title,
            description=content.description,
            media_type=MediaType.series,
            url=self.title_url(title_key),
            image_url=content.image_map.detail_background.path,
            thumbnail_url=content.image_map.detail_background.path,
            poster_url=content.image_map.detail_poster.path,
            poster_thumbnail_url=content.image_map.detail_poster.path,
            year=content.release_year,
            data_timestamp=data_timestamp,
            source_id=source.id,
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(content.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        self._set_title_update_at(upserted_title)
        self._set_expiry_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, season_number in enumerate(
            self.season_numbers(self._content(title.key)),
        ):
            season_key = self.build_season_key(title.key, season_number)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            upserted_season = Season(
                key=season_key,
                season_number=season_number,
                sort_order=sort_order,
                data_timestamp=self._season_files_data_timestamp(
                    season_key,
                    title.key,
                ),
                title_id=title.id,
            ).upsert(title, existing_season)

            self._upsert_episodes(upserted_season, title.key, season_number)
            self._set_season_update_at(upserted_season)

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_number: int,
    ) -> None:
        for sort_order, item in enumerate(
            self._season_episodes(title_key, season_number),
        ):
            episode_key = self.content_id(item.meta.id)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=item.title,
                episode_number=int(item.episode_number),
                url=self.video_url(episode_key),
                description=item.description,
                image_url=item.image_map.grid.path,
                thumbnail_url=item.image_map.grid.path,
                duration=item.view_options[0].media.duration,
                air_date=item.release_date,
                sort_order=sort_order,
                data_timestamp=self._episode_files_data_timestamp(
                    episode_key,
                    season.key,
                    title_key,
                ),
                season_id=season.id,
            ).upsert(season, existing_episode)


# TODO: Validate
class RokuSeriesImporter(RokuSeriesUpsert):
    pass
