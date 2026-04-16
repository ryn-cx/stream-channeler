# # TODO: Validate
# from collections.abc import Sequence
# from datetime import datetime, timedelta
# from typing import Any, override

# from diving_board import DivingBoard
# from diving_board.adjacent_series.models import AdjacentSeries as AdjacentSeriesModel
# from diving_board.playlist.models import PlaylistModel
# from diving_board.schedule.models import ScheduleModel
# from diving_board.season.models import SeasonModel
# from diving_board.vod.models import VodModel
# from loguru import logger
# from sqlmodel import Session, col, select

# from app.config import settings
# from app.episodes.models import Episode
# from app.plugins.models import File, Plugin
# from app.plugins.plugins.utils.base_plugin import BasePlugin, JSONFile
# from app.plugins.plugins.utils.base_plugin.files import GAPIJSON
# from app.seasons.models import Season
# from app.shows.models import Show
# from app.sources.models import Source

# client = DivingBoard()


# class VodJSON(GAPIJSON[VodModel]):
#     api_endpoint = client.vod

#     def __init__(self, db: Session, plugin: Plugin, vod_key: int) -> None:
#         self.unique_identifier = str(vod_key)
#         super().__init__(db, plugin)

#     @override
#     def _get(self) -> VodModel:
#         return self.api_endpoint.get(int(self.unique_identifier))  # type: ignore[attr-defined]


# class SeasonJSON(GAPIJSON[SeasonModel]):
#     api_endpoint = client.season

#     def __init__(self, db: Session, plugin: Plugin, season_key: int) -> None:
#         self.unique_identifier = str(season_key)
#         super().__init__(db, plugin)

#     @override
#     def _get(self) -> SeasonModel:
#         return self.api_endpoint.get(int(self.unique_identifier))  # type: ignore[attr-defined]


# class PlaylistJSON(GAPIJSON[PlaylistModel]):
#     api_endpoint = client.playlist

#     def __init__(self, db: Session, plugin: Plugin, season_key: int) -> None:
#         self.unique_identifier = str(season_key)
#         super().__init__(db, plugin)

#     @override
#     def _get(self) -> PlaylistModel:
#         return self.api_endpoint.get(int(self.unique_identifier))  # type: ignore[attr-defined]


# class AdjacentSeriesJSON(JSONFile[AdjacentSeriesModel]):
#     def __init__(
#         self,
#         db: Session,
#         plugin: Plugin,
#         series_key: int,
#         season_key: int,
#     ) -> None:
#         self._series_key = series_key
#         self._season_key = season_key
#         self.unique_identifier = str(series_key)
#         super().__init__(db, plugin)

#     @override
#     def _download(self) -> None:
#         with self._log_download(str(self._series_key)):
#             adjacent_series = client.adjacent_series
#             response = adjacent_series.get(self._series_key, self._season_key)
#             content = adjacent_series.dump_response(response)
#             self._write(content)

#     @override
#     def _parse(self, raw: Any) -> AdjacentSeriesModel:
#         return client.adjacent_series.parse(raw)


# class ScheduleJSON(JSONFile[ScheduleModel]):
#     def __init__(
#         self,
#         db: Session,
#         plugin: Plugin,
#         input_date: datetime,
#     ) -> None:
#         self._input_date = input_date
#         self.unique_identifier = str(input_date)
#         super().__init__(db, plugin)

#     @override
#     def _download(self) -> None:
#         with self._log_download(str(self._input_date)):
#             schedule = client.schedule
#             response = schedule.get(from_=self._input_date - timedelta(days=1))
#             content = schedule.dump_response(response)
#             self._write(content)

#     @override
#     def _parse(self, raw: Any) -> ScheduleModel:
#         return client.schedule.parse(raw)


# class FileMixin(BasePlugin, register=False):
#     client = client

#     @override
#     def __init__(
#         self,
#         db: Session,
#         *,
#         url: str | None = None,
#         source: Source | None = None,
#         show: Show | None = None,
#         season: Season | None = None,
#         episode: Episode | None = None,
#     ) -> None:
#         self.__first_season_key_cache: dict[str, int] = {}
#         self.__tv_show_key_cache: dict[str, int] = {}
#         self.__season_keys_cache: dict[str, list[int]] = {}
#         super().__init__(
#             db,
#             url=url,
#             source=source,
#             show=show,
#             season=season,
#             episode=episode,
#         )

#     def _playlist_json(
#         self,
#         season_key: int | str,
#     ) -> PlaylistJSON:
#         season_key = int(season_key)
#         return self._get_weakref_cached_file(
#             PlaylistJSON,
#             season_key,
#             lambda: PlaylistJSON(
#                 self.session,
#                 self.plugin,
#                 season_key,
#             ),
#         )

#     def _vod_json(
#         self,
#         vod_key: int | str,
#     ) -> VodJSON:
#         vod_key = int(vod_key)
#         return self._get_weakref_cached_file(
#             VodJSON,
#             vod_key,
#             lambda: VodJSON(
#                 self.session,
#                 self.plugin,
#                 vod_key,
#             ),
#         )

#     def _schedule_json(
#         self,
#         input_date: datetime,
#     ) -> ScheduleJSON:
#         cache_key = str(input_date)
#         return self._get_weakref_cached_file(
#             ScheduleJSON,
#             cache_key,
#             lambda: ScheduleJSON(
#                 self.session,
#                 self.plugin,
#                 input_date,
#             ),
#         )

#     def _season_json(
#         self,
#         season_key: int | str,
#     ) -> SeasonJSON:
#         season_key = int(season_key)
#         return self._get_weakref_cached_file(
#             SeasonJSON,
#             season_key,
#             lambda: SeasonJSON(
#                 self.session,
#                 self.plugin,
#                 season_key,
#             ),
#         )

#     def _adjacent_series_json(
#         self,
#         series_key: int | str,
#         season_key: int | str,
#     ) -> AdjacentSeriesJSON:
#         series_key = int(series_key)
#         season_key = int(season_key)
#         return self._get_weakref_cached_file(
#             AdjacentSeriesJSON,
#             season_key,
#             lambda: AdjacentSeriesJSON(
#                 self.session,
#                 self.plugin,
#                 series_key,
#                 season_key,
#             ),
#         )

#     def _get_first_season_key(self, season_key: int | str) -> int:
#         initial_season_file = self._season_json(season_key)
#         show_key = initial_season_file.parsed().metadata.series.series_id
#         other_seasons_file = self._adjacent_series_json(show_key, season_key)
#         for other_season in other_seasons_file.parsed().preceding_seasons:
#             return other_season.id

#         return int(season_key)

#     # region File Groups

#     def _tv_show_show_files(
#         self,
#         first_season_key: int,
#         show_key: int,
#     ) -> Sequence[SeasonJSON | AdjacentSeriesJSON]:
#         return [
#             # Required to detect changes to the show information.
#             self._season_json(first_season_key),
#             # Required to detect new seasons.
#             self._adjacent_series_json(show_key, first_season_key),
#         ]

#     def _movie_show_files(self, movie_key: int | str) -> Sequence[PlaylistJSON]:
#         return [
#             # This file has all of the information for movie shows.
#             self._playlist_json(movie_key),
#         ]

#     def _tv_show_season_files(
#         self,
#         season_key: int,
#         show_key: int,
#     ) -> Sequence[SeasonJSON | AdjacentSeriesJSON]:
#         return [
#             # Required to detect changes in the season.
#             self._season_json(season_key),
#             # Required to detect changes in later seasons.
#             self._adjacent_series_json(show_key, season_key),
#         ]

#     def _movie_season_files(self, movie_key: int | str) -> Sequence[PlaylistJSON]:
#         return [
#             # This file has all of the information for movie seasons.
#             self._playlist_json(movie_key),
#         ]

#     def _tv_show_episode_files(
#         self,
#         season_key: int,
#         episode_key: int,
#     ) -> Sequence[SeasonJSON | VodJSON]:
#         return [
#             # Required to detect new episodes.
#             self._season_json(season_key),
#             # Required to detect changes to the episode information.
#             self._vod_json(episode_key),
#         ]

#     def _movie_episode_files(
#         self,
#         movie_key: int | str,
#         episode_key: int,
#     ) -> Sequence[PlaylistJSON | VodJSON]:
#         return [
#             # Required for most episode information.
#             self._playlist_json(movie_key),
#             # Required for episode duration.
#             self._vod_json(episode_key),
#         ]

#     @override
#     def _show_files(
#         self,
#         show_key: str,
#     ) -> Sequence[SeasonJSON | AdjacentSeriesJSON | PlaylistJSON]:
#         if self._media_type == "TV Show":
#             return self._tv_show_show_files(
#                 self._first_season_key_from_file(show_key),
#                 self._tv_show_key_from_file(show_key),
#             )
#         return self._movie_show_files(show_key)

#     @override
#     def _season_files(
#         self,
#         season_key: int | str,
#     ) -> Sequence[SeasonJSON | AdjacentSeriesJSON | PlaylistJSON]:
#         if self._media_type == "TV Show":
#             show_key = self._season_json(season_key).parsed().metadata.series.series_id
#             return self._tv_show_season_files(int(season_key), show_key)
#         return self._movie_season_files(season_key)

#     @override
#     def _episode_files(
#         self,
#         season_key: int | str,
#         episode_key: int,
#     ) -> Sequence[SeasonJSON | VodJSON | PlaylistJSON]:
#         if self._media_type == "TV Show":
#             return self._tv_show_episode_files(int(season_key), episode_key)
#         return self._movie_episode_files(season_key, episode_key)

#     # endregion File Groups

#     # region Cached File Values

#     def _first_season_key_from_file(self, show_key: str) -> int:
#         if show_key not in self.__first_season_key_cache:
#             self.__first_season_key_cache[show_key] = self._get_first_season_key(
#                 show_key,
#             )
#         return self.__first_season_key_cache[show_key]

#     def _tv_show_key_from_file(self, show_key: str) -> int:
#         if show_key not in self.__tv_show_key_cache:
#             first_season_file = self._season_json(
#                 self._first_season_key_from_file(show_key),
#             )
#             self.__tv_show_key_cache[show_key] = (
#                 first_season_file.parsed().metadata.series.series_id
#             )
#         return self.__tv_show_key_cache[show_key]

#     def _season_keys(self, season_key: int | str) -> list[int]:
#         first_season_key = self._get_first_season_key(season_key)
#         first_season_file = self._season_json(first_season_key)
#         show_key = first_season_file.parsed().metadata.series.series_id
#         other_seasons_file = self._adjacent_series_json(show_key, first_season_key)

#         output = [int(season_key)]
#         output.extend(x.id for x in other_seasons_file.parsed().following_seasons)
#         return output

#     def _season_keys_from_json(self, show_key: str) -> list[int]:
#         if show_key not in self.__season_keys_cache:
#             self.__season_keys_cache[show_key] = self._season_keys(show_key)
#         return self.__season_keys_cache[show_key]

#     # endregion Cached File Values

#     # region Download

#     def _download_show_files(self, show_key: str) -> None:
#         logger.info(f"Downloading All Files For: {self._pretty_show_name(show_key)}")
#         if self._media_type == "TV Show":
#             self.__download_initial_tv_show(show_key)
#         else:
#             self.__download_initial_movie(show_key)

#     def __download_initial_tv_show(self, show_key: str) -> None:
#         # Download show-level files (season + adjacent series for first season)
#         self._season_json(show_key)
#         self._season_json(self._first_season_key_from_file(show_key))
#         self._adjacent_series_json(
#             self._tv_show_key_from_file(show_key),
#             self._first_season_key_from_file(show_key),
#         )
#         # Download season-level files
#         for season_key in self._season_keys_from_json(show_key):
#             self._season_json(season_key)
#             self._adjacent_series_json(
#                 self._tv_show_key_from_file(show_key),
#                 season_key,
#             )
#         # Download episode-level files
#         for season_key in self._season_keys_from_json(show_key):
#             season_json = self._season_json(season_key).parsed()
#             season_bucket = self.client.season.extract_bucket(season_json, "season")
#             for episode_data in season_bucket.items:
#                 self._vod_json(episode_data.id)

#     def __download_initial_movie(self, show_key: str) -> None:
#         # Download show/season-level files
#         self._playlist_json(show_key)
#         # Download episode-level files
#         playlist_json = self._playlist_json(show_key).parsed()
#         playlist_bucket = self.client.playlist.extract_bucket(
#             playlist_json,
#             "playlist",
#         )
#         for item in playlist_bucket.items:
#             self._vod_json(item.id)

#     # endregion Download

#     # region Preload

#     def _preload_show_season_episode_files(self, show_key: str) -> None:
#         if self._media_type == "TV Show":
#             self.__preload_tv_show_files(show_key)
#         else:
#             self.__preload_movie_files(show_key)

#     def __preload_tv_show_files(self, show_key: str) -> None:
#         all_file_keys: list[str] = []
#         for season_key in self._season_keys_from_json(show_key):
#             season_json = self._season_json(season_key)
#             all_file_keys.append(season_json.file_key())
#             if season_json.database_record.content:
#                 tv_show_key = season_json.parsed().metadata.series.series_id
#                 all_file_keys.append(
#                     self._adjacent_series_json(tv_show_key, season_key).file_key(),
#                 )
#                 season_data = season_json.parsed()
#                 season_bucket = self.client.season.extract_bucket(
#                     season_data,
#                     "season",
#                 )
#                 all_file_keys.extend(
#                     self._vod_json(episode_data.id).file_key()
#                     for episode_data in season_bucket.items
#                 )

#         if all_file_keys:
#             file_select = (
#                 select(File)
#                 .where(File.plugin == self.plugin)
#                 .where(col(File.key).in_(all_file_keys))
#             )
#             self.session.exec(file_select).all()

#     def __preload_movie_files(self, show_key: str) -> None:
#         playlist_file = self._playlist_json(show_key)
#         all_file_keys: list[str] = [playlist_file.file_key()]

#         if playlist_file.database_record.content:
#             playlist_json = playlist_file.parsed()
#             playlist_bucket = self.client.playlist.extract_bucket(
#                 playlist_json,
#                 "playlist",
#             )
#             all_file_keys.extend(
#                 self._vod_json(item.id).file_key() for item in playlist_bucket.items
#             )

#         file_select = (
#             select(File)
#             .where(File.plugin == self.plugin)
#             .where(col(File.key).in_(all_file_keys))
#         )
#         self.session.exec(file_select).all()

#     # endregion Preload
