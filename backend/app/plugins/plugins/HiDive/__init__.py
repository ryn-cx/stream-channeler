# # TODO: Validate
# import re
# from datetime import date, datetime, timedelta
# from functools import cache
# from typing import Any, override

# from diving_board.exceptions import HTTPError
# from diving_board.season.models import SeasonModel
# from loguru import logger
# from sqlmodel import Session, col, select

# from app.episodes.models import Episode
# from app.episodes.schemas import EpisodeInput
# from app.plugins.models import File
# from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
# from app.seasons.models import Season
# from app.seasons.schemas import SeasonInput
# from app.shows.models import Show
# from app.shows.schemas import ShowInput
# from app.sources.models import Source
# from app.sources.schemas import SourceInput
# from app.utils import tz_datetime

# from .files import (
#     AdjacentSeriesJSON,
#     FileMixin,
#     PlaylistJSON,
#     SeasonJSON,
# )


# class HiDivePlugin(FileMixin, register=True):
#     _VERSION = "0.0.1"

#     # region Initialization

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
#         self._media_type_value: str | None = None
#         super().__init__(
#             db,
#             url=url,
#             source=source,
#             show=show,
#             season=season,
#             episode=episode,
#         )

#     @classmethod
#     @cache
#     @override
#     def plugin_id(cls) -> str:
#         return "HiDive"

#     @classmethod
#     @cache
#     def _plugin_name(cls) -> str:
#         return "HiDive"

#     @classmethod
#     @cache
#     @override
#     def domains(cls) -> list[str]:
#         return ["hidive.com"]

#     # endregion

#     # region Import URL

#     @override
#     def import_url(self, url: str) -> list[URLImportResult]:
#         if match := re.match(self._tv_series_url_regex(), url):
#             show_key = match.group("season_key")
#             self._media_type = "TV Show"
#             self._validate_show_key(show_key)
#         elif match := re.match(self._movie_url_regex(), url):
#             show_key = match.group("movie_key")
#             self._media_type = "Movie"
#             self._validate_movie_key(show_key)
#         else:
#             msg = f"URL is not a valid {self._plugin_name()} URL: {url}"
#             raise InvalidURLError(msg)

#         self._preload_show_season_episode_files(show_key)
#         self._download_initial_files(show_key)
#         show = self.__upsert_source(show_key)
#         return [URLImportResult(show=show, whitelist_mode=False)]

#     # endregion

#     # region Update Source

#     @override
#     def update_source(self, source: Source) -> None:
#         schedule_calendar = self._schedule_json(source.data_timestamp)
#         schedule_group_list = self.client.schedule.extract_group_list(
#             schedule_calendar.parsed(),
#         )

#         for release in schedule_group_list.attributes.groups:
#             episode_text = (
#                 release.attributes.cards[0]
#                 .attributes.content[0]
#                 .attributes.elements[1]
#                 .attributes.text
#             )

#             if not isinstance(episode_text, str):
#                 msg = "Invalid episode text format in schedule calendar"
#                 raise TypeError(msg)

#             release_date = (
#                 release.attributes.cards[0]
#                 .attributes.content[0]
#                 .attributes.elements[0]
#                 .attributes.text
#             )
#             # TODO: There are some issues parsing here
#             if isinstance(release_date, str):
#                 release_date = datetime.fromisoformat(release_date).astimezone()

#             if not release_date:
#                 msg = "Unable to get release date from schedule calendar"
#                 raise TypeError(msg)

#             if show := self.db.exec(
#                 select(Show).where(
#                     Show.source == source,
#                     Show.name == episode_text.split(" - ")[1],
#                 ),
#             ).first():
#                 # There is no good way to know which season the episode belongs to so
#                 # just update everything.
#                 show.update_at = release_date
#                 for season in show.seasons:
#                     season.update_at = release_date

#         source.data_timestamp = schedule_calendar.data_timestamp
#         source.set_update_at(schedule_calendar.data_timestamp + timedelta(days=1))

#     # endregion

#     # region Update Media

#     @override
#     def update_show(self, show: Show) -> None:
#         show_key = show.active_children()[0].key
#         self._media_type = show.media_type
#         self.__preload_update_media(show_key)
#         for show_file in self._show_files(show_key):
#             show_file.download_if_outdated(show.update_at)
#         self.__upsert_source(show_key)

#     @override
#     def update_season(self, season: Season) -> None:
#         show_key = season.show.active_children()[0].key
#         self._media_type = season.show.media_type
#         self.__preload_update_media(show_key)
#         for season_file in self._season_files(int(season.key)):
#             season_file.download_if_outdated(season.update_at)
#         self.__upsert_source(show_key)

#     @override
#     def update_episode(self, episode: Episode) -> None:
#         show_key = episode.season.show.active_children()[0].key
#         self._media_type = episode.season.show.media_type
#         self.__preload_update_media(show_key)
#         for episode_file in self._episode_files(
#             int(episode.season.key),
#             int(episode.key),
#         ):
#             episode_file.download_if_outdated(episode.update_at)
#         self.__upsert_source(show_key)

#     def __preload_update_media(self, show_key: str) -> None:
#         self.__bootstrap_preload(show_key)
#         self._preload_show_season_episode_files(show_key)

#     def __bootstrap_preload(self, show_key: str) -> None:
#         """Preload initial files needed for _season_keys_from_json computation."""
#         if self._media_type == "TV Show":
#             file_keys = [SeasonJSON.file_key(show_key)]
#             file_select = (
#                 select(File)
#                 .where(File.plugin == self.plugin)
#                 .where(col(File.key).in_(file_keys))
#             )
#             self.db.exec(file_select).all()
#             season_json = self._season_json(show_key)
#             if season_json.database_record.content:
#                 tv_show_key = str(season_json.parsed().metadata.series.series_id)
#                 adj_keys = [AdjacentSeriesJSON.file_key(tv_show_key)]
#                 adj_select = (
#                     select(File)
#                     .where(File.plugin == self.plugin)
#                     .where(col(File.key).in_(adj_keys))
#                 )
#                 self.db.exec(adj_select).all()
#         else:
#             file_keys = [PlaylistJSON.file_key(show_key)]
#             file_select = (
#                 select(File)
#                 .where(File.plugin == self.plugin)
#                 .where(col(File.key).in_(file_keys))
#             )
#             self.db.exec(file_select).all()

#     # endregion

#     # region Regex

#     @classmethod
#     @cache
#     def _url_regex(cls) -> str:
#         return cls._tv_series_url_regex() + "|" + cls._movie_url_regex()

#     @classmethod
#     @cache
#     def _tv_series_url_regex(cls) -> str:
#         domain_regex = cls._domain_regex()
#         # Example URLs:
#         # https://www.hidive.com/series/1189
#         regex_string = r"\/season\/(?P<season_key>\d+)"
#         return domain_regex + regex_string

#     @classmethod
#     @cache
#     def _movie_url_regex(cls) -> str:
#         domain_regex = cls._domain_regex()
#         # Example URLs:
#         # https://www.hidive.com/playlist/20431
#         regex_string = r"\/playlist\/(?P<movie_key>\d+)"
#         return domain_regex + regex_string

#     # endregion

#     # region Class Methods

#     @classmethod
#     @cache
#     def _domain(cls) -> str:
#         return "hidive.com"

#     @classmethod
#     @cache
#     def _tv_show_url(cls, show_key: str | int) -> str:
#         # This will redirect to a season page
#         return f"{cls._base_url()}series/{show_key}"

#     @classmethod
#     @cache
#     def _movie_url(cls, movie_key: str | int) -> str:
#         return f"{cls._base_url()}playlist/{movie_key}"

#     @classmethod
#     @cache
#     def _episode_url(cls, episode_key: str | int) -> str:
#         return f"{cls._base_url()}video/{episode_key}"

#     # endregion

#     # region Properties

#     @property
#     def _media_type(self) -> str:
#         if not self._media_type_value:
#             msg = "Media type has not been set yet."
#             raise AttributeError(msg)
#         return self._media_type_value

#     @_media_type.setter
#     def _media_type(self, media_type: str) -> None:
#         if self._media_type_value and self._media_type_value != media_type:
#             msg = "Media type has already been set and cannot be changed."
#             raise AttributeError(msg)
#         self._media_type_value = media_type

#     # endregion

#     # region Cached Properties

#     def _show_from_db(self, show_key: str) -> Show | None:
#         existing_source = Source.get_from_memory(
#             self.db,
#             self.plugin,
#             self._plugin_name(),
#         )
#         if existing_source:
#             db_show_key = self._get_show_key_for_lookup(show_key)
#             return Show.get_from_memory(self.db, existing_source, db_show_key)
#         return None

#     def _seasons_dict_from_db(self, show_key: str) -> dict[str, Season]:
#         """Return a dictionary of seasons keyed by season key."""
#         if show := self._show_from_db(show_key):
#             return {season.key: season for season in show.seasons}
#         return {}

#     def _episodes_dict_from_db(self, show_key: str) -> dict[str, Episode]:
#         """Return a dictionary of episodes keyed by episode key."""
#         if show := self._show_from_db(show_key):
#             return {
#                 episode.key: episode
#                 for season in show.seasons
#                 for episode in season.episodes
#             }
#         return {}

#     def _season_episodes_dict_from_db(
#         self,
#         show_key: str,
#     ) -> dict[str, dict[str, Episode]]:
#         """Return a nested dictionary of episodes keyed by season key and episode key."""
#         if show := self._show_from_db(show_key):
#             return {
#                 season.key: {episode.key: episode for episode in season.episodes}
#                 for season in show.seasons
#             }
#         return {}

#     def _get_show_key_for_lookup(self, show_key: str) -> str:
#         """Get the show key based on media type."""
#         if self._media_type == "TV Show":
#             return self._get_show_key_from_season_key(show_key)
#         return show_key

#     def _get_show_key_from_season_key(self, season_key: str) -> str:
#         first_season_key = self._get_first_season_key(season_key)
#         first_season_file = self._season_json(first_season_key).parsed()
#         return str(first_season_file.metadata.series.series_id)

#     # endregion

#     # region Upsert

#     def __upsert_source(self, show_key: str) -> Show:
#         logger.info(f"Upserting show: {self._pretty_show_name(show_key)}")
#         existing_source = Source.get_from_memory(
#             self.db,
#             self.plugin,
#             self._plugin_name(),
#         )
#         source = SourceInput(
#             key=self._plugin_name(),
#             name=self._plugin_name(),
#             # TODO: Don't hardcode the favicon URL
#             favicon_url="https://static.diceplatform.com/prod/original/dce.hidive/settings/HIDIVE_Logo_iOS_1024x1024_281_29.Y3YMf.vMQ59.png?ts=1727963356",
#             update_at=tz_datetime.now() + timedelta(days=1),
#             data_timestamp=existing_source.data_timestamp
#             if existing_source
#             else tz_datetime.now(),
#         ).upsert(self.plugin, existing_source)
#         return self.__upsert_show(source, show_key)

#     def __upsert_show(self, source: Source, show_key: str) -> Show:
#         if existing_show := self._show_from_db(show_key):
#             existing_show.soft_delete()

#         if self._media_type == "TV Show":
#             show = self.__upsert_tv_show_show(source, show_key)
#         else:
#             show = self.__upsert_movie_show(source, show_key)

#         self.__upsert_seasons(show, show_key)
#         return show

#     def __upsert_tv_show_show(self, source: Source, show_key: str) -> Show:
#         first_season_file = self._season_json(
#             self._first_season_key_from_file(show_key),
#         ).parsed()

#         return ShowInput(
#             key=str(first_season_file.metadata.series.series_id),
#             name=first_season_file.metadata.series.title,
#             media_type="TV Show",
#             url=self._tv_show_url(first_season_file.metadata.series.series_id),
#             data_timestamp=self._show_timestamp(),
#         ).upsert(source, self._show_from_db(show_key))

#     def __upsert_movie_show(self, source: Source, show_key: str) -> Show:
#         playlist_json = self._playlist_json(show_key).parsed()
#         playlist_bucket = self.client.playlist.extract_bucket(
#             playlist_json,
#             "playlist",
#         )
#         movie_data = playlist_bucket.items[0]

#         return ShowInput(
#             key=show_key,
#             data_timestamp=self._show_timestamp(),
#             name=movie_data.title,
#             media_type="Movie",
#             description=movie_data.description,
#             url=self._movie_url(playlist_bucket.id),
#             image_url=movie_data.thumbnail_url,
#         ).upsert(source, self._show_from_db(show_key))

#     def __upsert_seasons(self, show: Show, show_key: str) -> None:
#         seasons: list[Season] = []
#         if self._media_type == "TV Show":
#             seasons.extend(
#                 self.__upsert_tv_show_season(show, season_key, show_key)
#                 for season_key in self._season_keys_from_json(show_key)
#             )
#         else:
#             seasons.append(self.__upsert_movie_season(show, show_key))
#         self.__upsert_episodes(seasons, show_key)

#     def __upsert_tv_show_season(
#         self,
#         show: Show,
#         season_key: int,
#         show_key: str,
#     ) -> Season:
#         season_json = self._season_json(season_key).parsed()

#         series_data = self.client.season.extract_series(season_json)
#         series_hero = self.client.season.extract_hero(season_json)
#         season_data = series_data.attributes.seasons.items[0]

#         sort_order = self._season_keys_from_json(show_key).index(season_key)

#         seasons_dict = self._seasons_dict_from_db(show_key)
#         season = SeasonInput(
#             key=str(season_key),
#             data_timestamp=self._season_timestamp(season_key),
#             sort_order=sort_order,
#             name=season_data.title,
#             url=self._tv_show_url(season_key),
#             image_url=series_hero.attributes.image.attributes.source,
#             season_number=season_data.season_number,
#         ).upsert(show, seasons_dict.get(str(season_key)))

#         return season

#     def __upsert_movie_season(self, show: Show, show_key: str) -> Season:
#         playlist_json = self._playlist_json(show_key).parsed()
#         playlist_bucket = self.client.playlist.extract_bucket(
#             playlist_json,
#             "playlist",
#         )
#         movie_data = playlist_bucket.items[0]

#         seasons_dict = self._seasons_dict_from_db(show_key)
#         season = SeasonInput(
#             key=show_key,
#             data_timestamp=self._show_timestamp(),
#             sort_order=0,
#             name=movie_data.title,
#             season_number=0,
#             url=self._movie_url(playlist_bucket.id),
#             image_url=movie_data.thumbnail_url,
#         ).upsert(show, seasons_dict.get(show_key))

#         return season

#     def __upsert_episodes(self, seasons: list[Season], show_key: str) -> None:
#         if self._media_type == "TV Show":
#             for season in seasons:
#                 season_json = self._season_json(int(season.key)).parsed()
#                 self.__upsert_tv_show_season_episodes(season, season_json, show_key)
#                 self.__set_season_update_at_using_episode_release_date(season)
#         else:
#             for season in seasons:
#                 self.__upsert_movie_episode(season, show_key)

#     def __upsert_tv_show_season_episodes(
#         self,
#         season: Season,
#         season_json: SeasonModel,
#         show_key: str,
#     ) -> None:
#         season_bucket = self.client.season.extract_bucket(season_json, "season")
#         for index, episode_data in enumerate(season_bucket.items):
#             self.__upsert_tv_show_episode(season, episode_data, index, show_key)

#     def __upsert_tv_show_episode(
#         self,
#         season: Season,
#         episode_data: Any,
#         sort_order: int,
#         show_key: str,
#     ) -> Episode:
#         vod_data = self._vod_json(episode_data.id).parsed()
#         # TODO: extract_vod_original_premiere was removed from diving_board.
#         # Replace with the new method to extract the premiere date from VodModel.
#         parsed_date = self.client.vod.extract_text_block(vod_data)
#         episode_date = parsed_date.date() if parsed_date else None

#         # Episode number needs to be parsed from the titles which seems to always be
#         # in the format "E# - Title"
#         episode_number = None
#         if match := re.match(r"^E(\d+)", episode_data.title):
#             episode_number = int(match.group(1))

#         season_episodes = self._season_episodes_dict_from_db(show_key)
#         episode = EpisodeInput(
#             key=str(episode_data.id),
#             data_timestamp=self._episode_timestamp(
#                 int(season.key),
#                 int(episode_data.id),
#             ),
#             url=self._episode_url(episode_data.id),
#             sort_order=sort_order,
#             description=episode_data.description,
#             image_url=episode_data.thumbnail_url,
#             episode_number=episode_number,
#             name=episode_data.title,
#             release_date=episode_date,
#             air_date=episode_date,
#             duration=episode_data.duration,
#         ).upsert(
#             season,
#             season_episodes.get(season.key, {}).get(str(episode_data.id)),
#         )

#         return episode

#     def __upsert_movie_episode(self, season: Season, show_key: str) -> Episode:
#         playlist_json = self._playlist_json(show_key).parsed()
#         playlist_bucket = self.client.playlist.extract_bucket(
#             playlist_json,
#             "playlist",
#         )
#         movie_data = playlist_bucket.items[0]

#         vod_data = self._vod_json(movie_data.id).parsed()
#         # TODO: extract_vod_original_premiere was removed from diving_board.
#         # Replace with the new method to extract the premiere date from VodModel.
#         parsed_date = self.client.vod.extract_text_block(vod_data)
#         episode_date = parsed_date.date() if parsed_date else None

#         season_episodes = self._season_episodes_dict_from_db(show_key)
#         episode = EpisodeInput(
#             key=str(movie_data.id),
#             data_timestamp=self._episode_timestamp(show_key, int(movie_data.id)),
#             url=self._episode_url(movie_data.id),
#             sort_order=0,
#             description=movie_data.description,
#             image_url=movie_data.thumbnail_url,
#             episode_number=0,
#             name=movie_data.title,
#             release_date=episode_date,
#             air_date=episode_date,
#             duration=int(movie_data.duration),
#         ).upsert(
#             season,
#             season_episodes.get(season.key, {}).get(str(movie_data.id)),
#         )

#         return episode

#     # endregion

#     # region Validation

#     def _validate_show_key(self, show_key: str) -> None:
#         try:
#             self._season_json(show_key)
#         except HTTPError as e:
#             raise InvalidURLError(e)

#     def _validate_movie_key(self, show_key: str) -> None:
#         try:
#             self._playlist_json(show_key)
#         except HTTPError as e:
#             raise InvalidURLError(e)

#     # endregion

#     # region Other

#     def __set_season_update_at_using_episode_release_date(
#         self,
#         season: Season,
#     ) -> None:
#         """Sets the season's update_at based on the latest episode release date.

#         The date will be set to 7 days after the latest episode's release date if that
#         date is newer than the current data_timestamp.
#         """
#         if not season.episodes:
#             return

#         latest_episode = max(
#             season.episodes,
#             key=lambda ep: ep.release_date or date.min,
#         )

#         if not (latest_episode and latest_episode.release_date):
#             return

#         time_delta = timedelta(days=7)
#         update_at = tz_datetime.combine(
#             latest_episode.release_date + time_delta,
#             datetime.min.time(),
#         )
#         season.set_update_at(update_at)

#     # endregion
