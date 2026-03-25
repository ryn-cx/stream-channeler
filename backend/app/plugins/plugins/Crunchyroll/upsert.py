from datetime import datetime, timedelta
from typing import override

from loguru import logger

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.plugins.plugins.Crunchyroll.files import Browse, FileMixin
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.sources.schemas import SourceInput
from app.utils import tz_datetime


class UpsertMixin(FileMixin, register=False):
    # region URL

    @classmethod
    def _episode_url(cls, episode_key: str) -> str:
        return f"{cls._base_url()}watch/{episode_key}"

    # region Upsert Source

    def _upsert_source(self, latest_browse_file: Browse) -> Source:
        source = Source.get_from_memory(self.db, self.plugin, self.plugin_key())
        timestamp = latest_browse_file.database_entry.data_timestamp
        return SourceInput(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=f"{self._base_url()}build/assets/img/favicons/favicon-v2-96x96.png",
            # Check for new data daily.
            update_at=timestamp + timedelta(days=1),
            data_timestamp=timestamp,
        ).upsert(self.plugin, source)

    # endregion Upsert Source

    # region Upsert Show

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.db, source, show_key)
        show_files = self._show_files(show_key=show_key)
        show_timestamp = self._oldest_file_timestamp(show_files)

        series_data = self._series_file(show_key).parsed().data[0]
        if force_reimport or not show or show.data_timestamp != show_timestamp:
            logger.info(f"Upserting show: {self._pretty_show_name(show_key)}")
            show = ShowInput(
                key=series_data.id,
                name=series_data.title,
                description=series_data.description,
                url=self._show_url(series_data.id),
                data_timestamp=show_timestamp,
                media_type=self._get_media_type(show_key),
            ).upsert(source, show)

        self._upsert_seasons(show, show_key=show_key, force_reimport=force_reimport)
        self._set_season_update_at_using_episode_release_date(show)
        return show

    @classmethod
    def _show_url(cls, show_key: str) -> str:
        return f"{cls._base_url()}series/{show_key}"

    def _get_media_type(self, show_key: str) -> str:
        # Crunchyroll mixes together all of the different media types together with no
        # specific way to differentiate between them the simplest workaround is assume
        # anything that has only a single season and single episode is a movie and
        # everything else is a tv show.
        season_keys = self._season_keys_from_file(show_key)
        if len(season_keys) != 1:
            return "TV Show"
        episode_keys = self._episode_keys_from_file(season_keys[0])
        if len(episode_keys) == 1:
            return "Movie"
        return "TV Show"

    def _set_season_update_at_using_episode_release_date(
        self,
        show: Show,
    ) -> None:
        """Sets the season's update_at based on the latest episode release date.

        The date will be set to 7 days after the latest episode's release date if that
        date is newer than the current data_timestamp.
        """
        time_delta = timedelta(days=7)
        for season in show.seasons:
            latest_episode = max(
                season.episodes,
                # return-value - This should return an error if the value is not
                # defined.
                key=lambda ep: ep.release_date,  # type: ignore[return-value, arg-type]
            )

            if latest_episode and latest_episode.release_date:
                season.set_update_at(
                    tz_datetime.combine(
                        latest_episode.release_date + time_delta,
                        datetime.max.time(),
                    ),
                )

    # endregion Upsert Show

    def _upsert_seasons(
        self,
        show: Show,
        *,
        show_key: str,
        force_reimport: bool = False,
    ) -> None:
        season_keys = self._season_keys_from_file(show_key)
        show.soft_delete_missing_children(season_keys)

        seasons_file = self._seasons_file(show_key)
        for i, season_data in enumerate(seasons_file.parsed().data):
            season = Season.get_from_memory(self.db, show, season_data.id)
            season_files = self._season_files(season_data.id, show.key)
            season_timestamp = self._oldest_file_timestamp(season_files)
            if (
                force_reimport
                or not season
                or season.data_timestamp != season_timestamp
            ):
                logger.info(f"Upserting season: {season_data.title}")
                season = SeasonInput(
                    key=season_data.id,
                    sort_order=i,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    data_timestamp=season_timestamp,
                ).upsert(show, season)

            self._upsert_episodes(season, force_reimport=force_reimport)

    def _upsert_episodes(
        self,
        season: Season,
        *,
        force_reimport: bool = False,
    ) -> None:
        episode_keys = self._episode_keys_from_file(season.key)
        season.soft_delete_missing_children(episode_keys)

        episode_files = self._episode_files(season.key)
        episode_timestamp = self._oldest_file_timestamp(episode_files)

        episodes_data = self._episodes_file(season.key).parsed()
        for i, episode_data in enumerate(episodes_data.data):
            episode = Episode.get_from_memory(self.db, season, episode_data.id)
            if (
                not force_reimport
                and episode
                and episode.data_timestamp == episode_timestamp
            ):
                continue

            logger.info(f"Upserting episode: {episode_data.title}")
            EpisodeInput(
                key=episode_data.id,
                url=self._episode_url(episode_data.id),
                sort_order=i,
                description=episode_data.description,
                image_url=episode_data.images.thumbnail[0][-1].source,
                episode_number=episode_data.episode_number,
                name=episode_data.title,
                release_date=episode_data.premium_available_date,
                air_date=episode_data.episode_air_date,
                duration=episode_data.duration_ms // 1000,
                data_timestamp=episode_timestamp,
            ).upsert(season, episode)

    # endregion
