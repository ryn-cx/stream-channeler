# TODO: Validate
from collections.abc import Sequence
from datetime import datetime, timedelta
from functools import cached_property
from typing import Any, override

from diving_board import DivingBoard
from diving_board.adjacent_series.models import AdjacentSeries as AdjacentSeriesModel
from diving_board.playlist.models import PlaylistModel
from diving_board.schedule.models import ScheduleModel
from diving_board.season.models import SeasonModel
from diving_board.vod.models import VodModel
from loguru import logger
from sqlmodel import Session, col, select

from app.config import settings
from app.episodes.models import Episode
from app.plugins.models import File, Plugin
from app.plugins.plugins.utils.base_files import JSONFile
from app.plugins.plugins.utils.base_plugin import BasePlugin
from app.plugins.plugins.utils.ip_validator import check_ip_not_matches
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

client = DivingBoard()


class VodJSON(JSONFile[VodModel]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        vod_id: int,
    ) -> None:
        self._vod_id = vod_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._vod_id)

    @override
    def _download(self) -> None:
        with self._log_download(str(self._vod_id)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            vod = client.vod
            response = vod.get(self._vod_id)
            content = vod.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> VodModel:
        return client.vod.parse(raw)


class SeasonJSON(JSONFile[SeasonModel]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        season_id: int,
    ) -> None:
        self._series_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._series_id)

    @override
    def _download(self) -> None:
        with self._log_download(str(self._series_id)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            season = client.season
            response = season.get(self._series_id)
            content = season.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> SeasonModel:
        return client.season.parse(raw)


class PlaylistJSON(JSONFile[PlaylistModel]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        season_id: int,
    ) -> None:
        self._series_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._series_id)

    @override
    def _download(self) -> None:
        with self._log_download(str(self._series_id)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            playlist = client.playlist
            response = playlist.get(self._series_id)
            content = playlist.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> PlaylistModel:
        return client.playlist.parse(raw)


class AdjacentSeriesJSON(JSONFile[AdjacentSeriesModel]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        series_id: int,
        season_id: int,
    ) -> None:
        self._series_id = series_id
        self._season_id = season_id
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._series_id)

    @override
    def _download(self) -> None:
        with self._log_download(str(self._series_id)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            adjacent_series = client.adjacent_series
            response = adjacent_series.get(self._series_id, self._season_id)
            content = adjacent_series.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> AdjacentSeriesModel:
        return client.adjacent_series.parse(raw)


class ScheduleJSON(JSONFile[ScheduleModel]):
    def __init__(
        self,
        db: Session,
        plugin: Plugin,
        input_date: datetime,
    ) -> None:
        self._input_date = input_date
        super().__init__(db, plugin)

    @override
    def unique_identifier(self) -> str:
        return str(self._input_date)

    @override
    def _download(self) -> None:
        with self._log_download(str(self._input_date)):
            check_ip_not_matches(settings.YOUTUBE_API_IP)
            schedule = client.schedule
            response = schedule.get(from_=self._input_date - timedelta(days=1))
            content = schedule.dump_response(response)
            self._write(content)

    @override
    def _parse(self, raw: Any) -> ScheduleModel:
        return client.schedule.parse(raw)


class FileMixin(BasePlugin, register=False):
    client = client

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
        self._seasons_json_cache: dict[int, SeasonJSON] = {}
        self._adjacent_series_json_cache: dict[int, AdjacentSeriesJSON] = {}
        self._schedule_json_cache: dict[str, ScheduleJSON] = {}
        self._vod_json_cache: dict[int, VodJSON] = {}
        self._playlist_json_cache: dict[int, PlaylistJSON] = {}
        super().__init__(
            db,
            url=url,
            source=source,
            show=show,
            season=season,
            episode=episode,
        )

    def _playlist_json(
        self,
        season_id: int | str,
    ) -> PlaylistJSON:
        season_id = int(season_id)
        return self._get_cached_file(
            self._playlist_json_cache,
            season_id,
            lambda: PlaylistJSON(
                self.db,
                self.plugin,
                season_id,
            ),
        )

    def _vod_json(
        self,
        vod_id: int | str,
    ) -> VodJSON:
        vod_id = int(vod_id)
        return self._get_cached_file(
            self._vod_json_cache,
            vod_id,
            lambda: VodJSON(
                self.db,
                self.plugin,
                vod_id,
            ),
        )

    def _schedule_json(
        self,
        input_date: datetime,
    ) -> ScheduleJSON:
        cache_key = str(input_date)
        return self._get_cached_file(
            self._schedule_json_cache,
            cache_key,
            lambda: ScheduleJSON(
                self.db,
                self.plugin,
                input_date,
            ),
        )

    def _season_json(
        self,
        season_id: int | str,
    ) -> SeasonJSON:
        season_id = int(season_id)
        return self._get_cached_file(
            self._seasons_json_cache,
            season_id,
            lambda: SeasonJSON(
                self.db,
                self.plugin,
                season_id,
            ),
        )

    def _adjacent_series_json(
        self,
        series_id: int | str,
        season_id: int | str,
    ) -> AdjacentSeriesJSON:
        series_id = int(series_id)
        season_id = int(season_id)
        return self._get_cached_file(
            self._adjacent_series_json_cache,
            season_id,
            lambda: AdjacentSeriesJSON(
                self.db,
                self.plugin,
                series_id,
                season_id,
            ),
        )

    def _get_first_season_id(self, season_id: int | str) -> int:
        initial_season_file = self._season_json(season_id)
        show_id = initial_season_file.parsed().metadata.series.series_id
        other_seasons_file = self._adjacent_series_json(show_id, season_id)
        for other_season in other_seasons_file.parsed().preceding_seasons:
            return other_season.id

        return int(season_id)

    # region File Groups

    def _tv_show_show_files(
        self,
        first_season_id: int,
        show_id: int,
    ) -> Sequence[SeasonJSON | AdjacentSeriesJSON]:
        return [
            # Required to detect changes to the show information.
            self._season_json(first_season_id),
            # Required to detect new seasons.
            self._adjacent_series_json(show_id, first_season_id),
        ]

    def _movie_show_files(self, movie_id: int | str) -> Sequence[PlaylistJSON]:
        return [
            # This file has all of the information for movie shows.
            self._playlist_json(movie_id),
        ]

    def _tv_show_season_files(
        self,
        season_id: int,
        show_id: int,
    ) -> Sequence[SeasonJSON | AdjacentSeriesJSON]:
        return [
            # Required to detect changes in the season.
            self._season_json(season_id),
            # Required to detect changes in later seasons.
            self._adjacent_series_json(show_id, season_id),
        ]

    def _movie_season_files(self, movie_id: int | str) -> Sequence[PlaylistJSON]:
        return [
            # This file has all of the information for movie seasons.
            self._playlist_json(movie_id),
        ]

    def _tv_show_episode_files(
        self,
        season_id: int,
        episode_id: int,
    ) -> Sequence[SeasonJSON | VodJSON]:
        return [
            # Required to detect new episodes.
            self._season_json(season_id),
            # Required to detect changes to the episode information.
            self._vod_json(episode_id),
        ]

    def _movie_episode_files(
        self,
        movie_id: int | str,
        episode_id: int,
    ) -> Sequence[PlaylistJSON | VodJSON]:
        return [
            # Required for most episode information.
            self._playlist_json(movie_id),
            # Required for episode duration.
            self._vod_json(episode_id),
        ]

    @override
    def _show_files(self) -> Sequence[SeasonJSON | AdjacentSeriesJSON | PlaylistJSON]:
        if self._media_type == "TV Show":
            return self._tv_show_show_files(
                self._first_season_id_from_file,
                self._tv_show_id_from_file,
            )
        return self._movie_show_files(self._show_id)

    @override
    def _season_files(
        self,
        season_id: int | str,
    ) -> Sequence[SeasonJSON | AdjacentSeriesJSON | PlaylistJSON]:
        if self._media_type == "TV Show":
            show_id = self._season_json(season_id).parsed().metadata.series.series_id
            return self._tv_show_season_files(int(season_id), show_id)
        return self._movie_season_files(self._show_id)

    @override
    def _episode_files(
        self,
        season_id: int | str,
        episode_id: int,
    ) -> Sequence[SeasonJSON | VodJSON | PlaylistJSON]:
        if self._media_type == "TV Show":
            return self._tv_show_episode_files(int(season_id), episode_id)
        return self._movie_episode_files(self._show_id, episode_id)

    # endregion File Groups

    # region Timestamps

    def _show_timestamp(self) -> datetime:
        return super()._show_timestamp()

    def _season_timestamp(self, season_id: int | str) -> datetime:
        return super()._season_timestamp(season_id)

    def _episode_timestamp(
        self,
        season_id: int | str,
        episode_id: int,
    ) -> datetime:
        return super()._episode_timestamp(season_id, episode_id)

    # endregion Timestamps

    # region Cached File Values

    @cached_property
    def _first_season_id_from_file(self) -> int:
        return self._get_first_season_id(self._show_id)

    @cached_property
    def _tv_show_id_from_file(self) -> int:
        first_season_file = self._season_json(self._first_season_id_from_file)
        return first_season_file.parsed().metadata.series.series_id

    def _season_ids(self, season_id: int | str) -> list[int]:
        first_season_id = self._get_first_season_id(season_id)
        first_season_file = self._season_json(first_season_id)
        show_id = first_season_file.parsed().metadata.series.series_id
        other_seasons_file = self._adjacent_series_json(show_id, first_season_id)

        output = [int(season_id)]
        output.extend(x.id for x in other_seasons_file.parsed().following_seasons)
        return output

    @cached_property
    def _season_ids_from_json(self) -> list[int]:
        return self._season_ids(self._show_id)

    # endregion Cached File Values

    # region Download

    def _download_initial_files(self) -> None:
        logger.info(f"Downloading All Files For: {self._pretty_show_name()}")
        if self._media_type == "TV Show":
            self.__download_initial_tv_show()
        else:
            self.__download_initial_movie()

    def __download_initial_tv_show(self) -> None:
        # Download show-level files (season + adjacent series for first season)
        self._season_json(self._show_id)
        self._season_json(self._first_season_id_from_file)
        self._adjacent_series_json(
            self._tv_show_id_from_file,
            self._first_season_id_from_file,
        )
        # Download season-level files
        for season_id in self._season_ids_from_json:
            self._season_json(season_id)
            self._adjacent_series_json(self._tv_show_id_from_file, season_id)
        # Download episode-level files
        for season_id in self._season_ids_from_json:
            season_json = self._season_json(season_id).parsed()
            season_bucket = self.client.season.extract_bucket(season_json, "season")
            for episode_data in season_bucket.items:
                self._vod_json(episode_data.id)

    def __download_initial_movie(self) -> None:
        # Download show/season-level files
        self._playlist_json(self._show_id)
        # Download episode-level files
        playlist_json = self._playlist_json(self._show_id).parsed()
        playlist_bucket = self.client.playlist.extract_bucket(
            playlist_json,
            "playlist",
        )
        for item in playlist_bucket.items:
            self._vod_json(item.id)

    # endregion Download

    # region Preload

    def _preload_show_season_episode_files(self) -> None:
        if self._media_type == "TV Show":
            self.__preload_tv_show_files()
        else:
            self.__preload_movie_files()

    def __preload_tv_show_files(self) -> None:
        all_file_keys: list[str] = []
        for season_id in self._season_ids_from_json:
            all_file_keys.append(SeasonJSON.file_key(str(season_id)))
            season_json = self._season_json(season_id)
            if season_json.has_file_content():
                show_id = season_json.parsed().metadata.series.series_id
                all_file_keys.append(AdjacentSeriesJSON.file_key(str(show_id)))
                season_data = season_json.parsed()
                season_bucket = self.client.season.extract_bucket(
                    season_data,
                    "season",
                )
                all_file_keys.extend(
                    VodJSON.file_key(str(episode_data.id))
                    for episode_data in season_bucket.items
                )

        if all_file_keys:
            file_select = (
                select(File)
                .where(File.plugin == self.plugin)
                .where(col(File.key).in_(all_file_keys))
            )
            self._add_all_to_preload_cache(file_select)

    def __preload_movie_files(self) -> None:
        all_file_keys: list[str] = [PlaylistJSON.file_key(self._show_id)]

        playlist_file = self._playlist_json(self._show_id)
        if playlist_file.has_file_content():
            playlist_json = playlist_file.parsed()
            playlist_bucket = self.client.playlist.extract_bucket(
                playlist_json,
                "playlist",
            )
            all_file_keys.extend(
                VodJSON.file_key(str(item.id)) for item in playlist_bucket.items
            )

        file_select = (
            select(File)
            .where(File.plugin == self.plugin)
            .where(col(File.key).in_(all_file_keys))
        )
        self._add_all_to_preload_cache(file_select)

    # endregion Preload
