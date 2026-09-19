# TODO: Validate
"""Writing what The Roku Channel says about a series into the database."""

from __future__ import annotations

from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Roku.shared import (
    RokuImporter,
    RokuShared,
    build_season_key,
    content_id,
    first_episode_key,
    season_episodes,
    season_numbers,
    split_season_key,
    title_url,
    video_url,
)
from plugins.utils.base_plugin.media_type import MediaType
from plugins.utils.base_plugin.url import ParsedURL

if TYPE_CHECKING:
    from collections.abc import Sequence

    from nana.content.models import Episode2 as SeasonEpisode

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class RokuSeriesFiles(RokuShared, ABC):
    # TODO: Validate
    def _season_episodes(
        self,
        title_key: str,
        season_number: int,
    ) -> list[SeasonEpisode]:
        episode_key = first_episode_key(self._content(title_key), season_number)
        return season_episodes(self.season_episodes_file(episode_key).parsed())

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        _title_key, season_number = split_season_key(season_key)
        episode_key = first_episode_key(self._content(title_key), season_number)
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
            build_season_key(title_key, season_number)
            for season_number in season_numbers(self._content(title_key))
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
                content_id(episode.meta.id)
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

        # A season carries its number after its id, an episode does not, and only
        # an episode is a title of its own to point at.
        title_key = content_id(series.meta.id)
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
            url=title_url(title_key),
            image_url=content.image_map.detail_background.path,
            thumbnail_url=content.image_map.detail_background.path,
            poster_url=content.image_map.detail_poster.path,
            poster_thumbnail_url=content.image_map.detail_poster.path,
            year=content.release_year,
            data_timestamp=data_timestamp,
            source_id=source.id,
            update_at=data_timestamp + timedelta(days=7),
        ).upsert(source, existing_title)
        upserted_title.upsert_genres(content.genres)

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, season_number in enumerate(
            season_numbers(self._content(title.key)),
        ):
            season_key = build_season_key(title.key, season_number)
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
            episode_key = content_id(item.meta.id)
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
                url=video_url(episode_key),
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
