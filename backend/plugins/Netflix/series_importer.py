# TODO: Validate
"""Writing what Netflix says about a series into the database."""

from __future__ import annotations

from abc import ABC
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, override

from app.episodes.models import Episode
from app.seasons.models import Season
from app.titles.models import Title
from app.tmdb_media.keys import watch_identifier
from plugins.Netflix.shared import NetflixImporter, NetflixShared
from plugins.utils.base_plugin.media_type import MediaType

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class NetflixSeriesFiles(NetflixShared, ABC):
    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the title and new seasons.
        return [self.title_file(title_key), self.seasons_file(title_key)]

    # TODO: Validate
    @override
    def _season_files(self, season_key: str, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            self.season_episodes_file(season_key),
            self.seasons_file(title_key),
        ]

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
            str(season.video_id) for season in self.seasons_file(title_key).seasons()
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
            episode_keys += [
                str(episode.video_id)
                for episode in self.season_episodes_file(season_key).episodes()
            ]
        return episode_keys


# TODO: Validate
class NetflixSeriesUpsert(NetflixSeriesFiles, NetflixImporter, ABC):
    # TODO: Validate
    def _available_at(self, messaging: str, data_timestamp: datetime) -> datetime:
        date_text = " ".join(messaging.removeprefix("Available").split())
        if "," not in date_text:
            date_text = f"{date_text}, {data_timestamp.year}"
        return datetime.strptime(date_text, "%B %d, %Y").replace(
            tzinfo=data_timestamp.tzinfo,
        )

    # TODO: Validate
    def _set_season_update_at(
        self,
        season: Season,
        season_video_key: str | int,
        data_timestamp: datetime,
    ) -> None:
        season.set_update_at(
            self._staggered_monthly_update_at(season.key, data_timestamp),
        )
        for episode in self.season_episodes_file(season_video_key).episodes():
            if episode.availability_date_messaging:
                available_at = self._available_at(
                    episode.availability_date_messaging,
                    data_timestamp,
                )
                # The date listed doesn't have a specific time so check it once on the
                # date, again halway through the day and one more time at the end of the
                # day.
                season.set_update_at(available_at)
                season.set_update_at(available_at + timedelta(hours=12))
                season.set_update_at(available_at + timedelta(days=1))

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
    ) -> Title:
        existing_title = Title.get_from_memory(self.session, source, title_key)
        title_data = self.title_file(title_key).parsed()
        upserted_title = Title(
            key=title_key,
            name=title_data.title,
            description=title_data.contextual_synopsis.text,
            media_type=MediaType.series,
            year=title_data.latest_year,
            url=self.title_url(title_key),
            image_url=title_data.boxart_high_res.url,
            thumbnail_url=title_data.boxart.url,
            data_timestamp=self._title_files_data_timestamp(title_key),
            source_id=source.id,
        ).upsert(
            source,
            existing_title,
        )
        upserted_title.upsert_genres(self._genre_names(title_data))

        self._upsert_seasons(upserted_title)
        self._soft_delete_missing_seasons_and_episodes(title_key)
        self.add_title_to_plugin_channels(upserted_title)

        self._set_title_update_at(upserted_title)
        return upserted_title

    # TODO: Validate
    def _upsert_seasons(self, title: Title) -> None:
        for sort_order, season_data in enumerate(
            self.seasons_file(title.key).seasons(),
        ):
            season_key = str(season_data.video_id)
            existing_season = Season.get_from_memory(self.session, title, season_key)
            data_timestamp = self._season_files_data_timestamp(
                season_key,
                title.key,
            )
            upserted_season = Season(
                key=season_key,
                name=season_data.title,
                season_number=sort_order + 1,
                sort_order=sort_order,
                data_timestamp=data_timestamp,
                title_id=title.id,
            ).upsert(title, existing_season)
            self._set_season_update_at(
                upserted_season,
                season_data.video_id,
                data_timestamp,
            )

            self._upsert_episodes(
                upserted_season,
                title.key,
                season_data.video_id,
            )

    # TODO: Validate
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        season_video_key: int,
    ) -> None:
        for sort_order, episode_data in enumerate(
            self.season_episodes_file(season_video_key).episodes(),
        ):
            episode_key = str(episode_data.video_id)
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            Episode(
                key=episode_key,
                watch_identifier=watch_identifier(self.plugin_name(), episode_key),
                name=episode_data.title,
                episode_number=episode_data.number,
                url=self.episode_url(episode_key),
                description=episode_data.contextual_synopsis.text,
                image_url=episode_data.artwork.url,
                thumbnail_url=episode_data.artwork.url,
                duration=episode_data.runtime_sec,
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
class NetflixSeriesImporter(NetflixSeriesUpsert):
    pass
