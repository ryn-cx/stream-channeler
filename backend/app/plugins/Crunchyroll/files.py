# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache, cached_property
from typing import Any, override

from chirashi import Chirashi
from chirashi.browse_series import models as browse_series_models
from chirashi.episodes import models as episodes_models
from chirashi.exceptions import HTTPError
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models
from loguru import logger
from sqlmodel import Session, col, select

from app.config import settings
from app.media.models import Episode, File, Plugin, Season, Show, Source
from app.plugins.utils.base_files import JSONFile
from app.plugins.utils.base_plugin import BasePlugin
from app.plugins.utils.ip_validator import check_ip_not_matches


@cache
def chirashi_client() -> Chirashi:
    return Chirashi()


class Series(JSONFile[series_models.Series]):
    def __init__(self, db: Session, plugin: Plugin, show_id: str) -> None:
        self.__show_id = show_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_id

    def _download(self) -> None:
        with self._log_download(self.__show_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            series = chirashi_client().series
            try:
                response = series.get(self.__show_id)
                content = series.dump_response(response)
                self._write(content)
            # Occurs when a user puts in an invalid URL.
            except HTTPError as e:
                if str(e) != "Unexpected response status code: 404":
                    raise

                self._write("")

    @override
    def _parse(self, raw: Any) -> series_models.Series:
        return chirashi_client().series.parse(raw)


class Seasons(JSONFile[seasons_models.Seasons]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        show_id: str,
    ) -> None:
        self.__show_id = show_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__show_id

    def _download(self) -> None:
        with self._log_download(self.__show_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            seasons = chirashi_client().seasons
            response = seasons.get(self.__show_id)
            content = seasons.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> seasons_models.Seasons:
        return chirashi_client().seasons.parse(raw)


class Episodes(JSONFile[episodes_models.Episodes]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        season_id: str,
    ) -> None:
        self.__season_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return self.__season_id

    def _download(self) -> None:
        with self._log_download(self.__season_id):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            episodes = chirashi_client().episodes
            response = episodes.get(self.__season_id)
            content = episodes.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> episodes_models.Episodes:
        return chirashi_client().episodes.parse(raw)


class Browse(JSONFile[list[browse_series_models.Datum]]):
    IMMUTABLE: bool = True

    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        last_update_datetime: datetime,
    ) -> None:
        self._last_update_datetime = last_update_datetime
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._last_update_datetime)

    def _download(self) -> None:
        with self._log_download(str(self._last_update_datetime)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            browse_series = chirashi_client().browse_series
            response = browse_series.get_since_datetime(
                end_datetime=self._last_update_datetime,
            )
            content = browse_series.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> list[browse_series_models.Datum]:
        parsed_pages = [chirashi_client().browse_series.parse(page) for page in raw]
        return chirashi_client().browse_series.extract_entries(parsed_pages)


class FileMixin(BasePlugin, register=False):
    @override
    def __init__(
        self,
        db: Session,
        *,
        url: str | None = None,
        source: Source | None = None,
        show: Show | None = None,
        season: Season | None = None,
        episode: Episode | None = None,
    ) -> None:
        self.__series_file: dict[str, Series] = {}
        self.__seasons_file: dict[str, Seasons] = {}
        self.__episodes_file: dict[str, Episodes] = {}
        self.__browse_file: dict[datetime, Browse] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    # region File Cache

    def _series_file(self, show_id: str) -> Series:
        return self._get_cached_file(
            self.__series_file,
            show_id,
            lambda: Series(self.db, self.plugin, show_id),
        )

    def _seasons_file(self, show_id: str) -> Seasons:
        return self._get_cached_file(
            self.__seasons_file,
            show_id,
            lambda: Seasons(self.db, self.plugin, show_id),
        )

    def _episodes_file(self, season_id: str) -> Episodes:
        return self._get_cached_file(
            self.__episodes_file,
            season_id,
            lambda: Episodes(self.db, self.plugin, season_id),
        )

    def _browse_file(self, last_update_datetime: datetime) -> Browse:
        return self._get_cached_file(
            self.__browse_file,
            last_update_datetime,
            lambda: Browse(self.db, self.plugin, last_update_datetime),
        )

    # endregion File Cache

    # region File Groups

    def _show_files(self, show_id: str) -> Sequence[Series | Seasons]:
        return [
            # Required to detect changes to the show.
            self._series_file(show_id),
            # Required to detect new seasons.
            self._seasons_file(show_id),
        ]

    def _season_files(
        self,
        show_id: str,
        season_id: str,
    ) -> Sequence[Seasons | Episodes]:
        return [
            # Required to detect changes to the season.
            self._seasons_file(show_id),
            # Required to detect new episodes.
            self._episodes_file(season_id),
        ]

    def _episode_files(self, season_id: str) -> Sequence[Episodes]:
        # Required to detect changes to the episode.
        return [self._episodes_file(season_id)]

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self, show_id: str) -> datetime:
        return super()._show_timestamp(show_id)

    def _season_timestamp(self, show_id: str, season_id: str) -> datetime:
        return super()._season_timestamp(show_id, season_id)

    def _episode_timestamp(self, season_id: str) -> datetime:
        return super()._episode_timestamp(season_id)

    # endregion Timestamps

    # region Cached File Values

    @cached_property
    def _season_ids_from_file(self) -> list[str]:
        return [
            season_data.id
            for season_data in self._seasons_file(self._show_id).parsed().data
        ]

    @cached_property
    def _episode_ids_from_file(self) -> list[str]:
        return [
            episode_data.id
            for season_id in self._season_ids_from_file
            for episode_data in self._episodes_file(season_id).parsed().data
        ]

    # endregion Cached File Values

    # region Download

    def _download_initial_files(self) -> None:
        logger.info(f"Downloading All Files For: {self._pretty_show_name()}")
        self.__download_initial_series()
        self.__download_initial_seasons()
        self.__download_initial_episodes()

    def __download_initial_series(self) -> None:
        self._series_file(self._show_id)

    def __download_initial_seasons(self) -> None:
        self._seasons_file(self._show_id)

    def __download_initial_episodes(self) -> None:
        for season_id in self._season_ids_from_file:
            self._episodes_file(season_id)

    # endregion Download

    # region Preload

    def _preload_show_season_episode_files(self) -> None:
        self.__preload_show_files()
        self.__preload_season_files()
        self.__preload_episode_files()

    def __preload_show_files(self) -> None:
        show_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        Series.file_key(self._show_id),
                        Seasons.file_key(self._show_id),
                    ],
                ),
            )
        )
        self._add_all_to_preload_cache(show_file_select)

    def __preload_season_files(self) -> None:
        season_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        Seasons.file_key(self._show_id),
                    ],
                ),
            )
        )
        self._add_all_to_preload_cache(season_file_select)

    def __preload_episode_files(self) -> None:
        episode_file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(
                col(File.key).in_(
                    [
                        Episodes.file_key(season_id)
                        for season_id in self._season_ids_from_file
                    ],
                ),
            )
        )
        self._add_all_to_preload_cache(episode_file_select)

    def _preload_latest_browse_file(self) -> File | None:
        statement = (
            select(File)
            .where(
                File.plugin == self.plugin,
                col(File.key).startswith(f"{Browse.__name__}/"),
            )
            .order_by(col(File.data_timestamp).desc())
        )
        return self._add_first_to_preload_cache(statement)

    # endregion Preload
