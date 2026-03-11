from datetime import date, datetime, timedelta
from typing import override

from loguru import logger

from app.episodes.schemas import EpisodeInput
from app.plugins.plugins.Crunchyroll.files import FileMixin
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.sources.schemas import SourceInput
from app.utils import tz_datetime


class UpsertMixin(FileMixin, register=False):
    # region Upsert

    def _upsert_source(self, show_key: str) -> Source:
        logger.info(f"Upserting show: {self._pretty_show_name(show_key)}")
        source = Source.get_from_memory(self.db, self.plugin, self._plugin_name())
        source = SourceInput(
            key=self._plugin_name(),
            name=self._plugin_name(),
            # TODO: Don't hardcode the favicon URL
            favicon_url=f"{self._base_url()}build/assets/img/favicons/favicon-v2-96x96.png",
            # Check for new data daily.
            update_at=self._latest_browse_file.get_data_timestamp() + timedelta(days=1),
            data_timestamp=self._latest_browse_file.get_data_timestamp(),
        ).upsert(self.plugin, source)
        self._upsert_show(source, show_key=show_key)
        return source

    @override
    def _upsert_show(
        self,
        source: Source,
        *,
        show_key: str = "",
        force_reimport: bool = False,
    ) -> None:
        # Soft delete everything then re-import everything to manage deleted entries.
        if existing_show := Show.get_from_memory(self.db, source, show_key):
            existing_show.soft_delete()

        series_file = self._series_file(show_key)
        series_data = series_file.parsed().data[0]

        show = ShowInput(
            key=series_data.id,
            name=series_data.title,
            # This isn't technically a TV Series or Movie because Crunchyroll mixes them
            # together. "Anime Series" is good enough for the majority of entries even
            # though Crunchyroll does have some live action content.
            media_type="Anime Series",
            description=series_data.description,
            url=self._show_url(series_data.id),
            data_timestamp=self._show_timestamp(series_data.id),
        ).upsert(source, existing_show)
        self.__upsert_seasons(show, show_key=show_key)
        self.__set_season_update_at_using_episode_release_date(show)

    def __upsert_seasons(self, show: Show, *, show_key: str) -> None:
        seasons_file = self._seasons_file(show_key)
        seasons_data = seasons_file.parsed().data
        season_data_dict = {season_data.id: season_data for season_data in seasons_data}
        season_dict_lookup = {season.key: season for season in show.seasons}

        seasons: list[Season] = []
        for i, season_key in enumerate(self._season_keys_from_file(show_key)):
            season_data = season_data_dict[season_key]

            seasons.append(
                SeasonInput(
                    key=season_data.id,
                    sort_order=i,
                    name=season_data.title,
                    season_number=season_data.season_number,
                    data_timestamp=self._season_timestamp(season_key),
                ).upsert(show, season_dict_lookup.get(season_data.id)),
            )
        self.__upsert_episodes(seasons)

    @override
    def _upsert_season(
        self,
        show: Show,
        season_key: str,
        *,
        force_reimport: bool = False,
    ) -> Season:
        seasons_file = self._seasons_file(show.key)
        seasons_data = seasons_file.parsed().data
        season_data_dict = {sd.id: sd for sd in seasons_data}
        season_data = season_data_dict[season_key]

        existing = Season.get_from_memory(self.db, show, season_key)
        season = SeasonInput(
            key=season_data.id,
            sort_order=self._season_keys_from_file(show.key).index(season_key),
            name=season_data.title,
            season_number=season_data.season_number,
            data_timestamp=self._season_timestamp(season_key),
        ).upsert(show, existing)
        self.__upsert_episodes([season])
        return season

    def __upsert_episodes(self, seasons: list[Season]) -> None:
        for season in seasons:
            episodes_file = self._episodes_file(season.key)
            episodes_data = episodes_file.parsed()
            episode_dict_lookup = {episode.key: episode for episode in season.episodes}
            for i, episode_data in enumerate(episodes_data.data):
                EpisodeInput(
                    key=episode_data.id,
                    url=self._episode_url(episode_data.id),
                    sort_order=i,
                    description=episode_data.description,
                    image_url=episode_data.images.thumbnail[0][-1].source,
                    episode_number=episode_data.episode_number,
                    name=episode_data.title,
                    release_date=episode_data.premium_available_date.date()
                    if episode_data.premium_available_date
                    else None,
                    air_date=episode_data.episode_air_date.date()
                    if episode_data.episode_air_date
                    else None,
                    duration=episode_data.duration_ms // 1000,
                    data_timestamp=self._episode_timestamp(season.key),
                ).upsert(season, episode_dict_lookup.get(episode_data.id))

    @override
    def _upsert_episode(
        self,
        season: Season,
        episode_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        episodes_data = self._episodes_file(season.key).parsed()
        episode_dict_lookup = {episode.key: episode for episode in season.episodes}
        for i, episode_data in enumerate(episodes_data.data):
            if episode_data.id == episode_key:
                EpisodeInput(
                    key=episode_data.id,
                    url=self._episode_url(episode_data.id),
                    sort_order=i,
                    description=episode_data.description,
                    image_url=episode_data.images.thumbnail[0][-1].source,
                    episode_number=episode_data.episode_number,
                    name=episode_data.title,
                    release_date=episode_data.premium_available_date.date()
                    if episode_data.premium_available_date
                    else None,
                    air_date=episode_data.episode_air_date.date()
                    if episode_data.episode_air_date
                    else None,
                    duration=episode_data.duration_ms // 1000,
                    data_timestamp=self._episode_timestamp(season.key),
                ).upsert(season, episode_dict_lookup.get(episode_data.id))
                break

    def __set_season_update_at_using_episode_release_date(
        self,
        show: Show,
    ) -> None:
        """Sets the season's update_at based on the latest episode release date.

        The date will be set to 7 days after the latest episode's release date if that
        date is newer than the current data_timestamp.
        """
        time_delta: timedelta = timedelta(days=7)
        for season in show.seasons:
            latest_episode = max(
                season.episodes,
                key=lambda ep: ep.release_date or date.min,
            )

            if not (latest_episode and latest_episode.release_date):
                return

            season.set_update_at(
                tz_datetime.combine(
                    latest_episode.release_date + time_delta,
                    datetime.min.time(),
                ),
            )

    # endregion
