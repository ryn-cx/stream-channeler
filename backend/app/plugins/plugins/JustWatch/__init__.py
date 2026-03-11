# # TODO: Validate
# import re
# from collections.abc import Sequence
# from datetime import date, datetime, timedelta
# from difflib import get_close_matches
# from functools import cache
# from typing import override
# from urllib.parse import parse_qs, urlparse

# from just_scrape.custom_buy_box_offers import (
#     response_models as custom_buy_box_offers_models,
# )
# from just_scrape.url_title_details import response_models as url_title_details_models
# from loguru import logger
# from sqlmodel import col, select

# from app.episodes.models import Episode
# from app.episodes.schemas import EpisodeInput
# from app.plugins.models import File
# from app.plugins.plugins.JustWatch.files import (
#     FileMixin,
#     NewTitles,
#     UrlTitleDetails,
# )
# from app.plugins.plugins.utils.abstract_plugin import URLImportResult
# from app.seasons.models import Season
# from app.seasons.schemas import SeasonInput
# from app.shows.models import Show
# from app.shows.schemas import ShowInput
# from app.sources.models import Source
# from app.sources.schemas import SourceInput
# from app.utils import strict_re, tz_datetime


# class JustWatch(FileMixin, register=True):
#     _VERSION = "0.0.1"

#     # region Import URL

#     @override
#     def import_url(self, url: str) -> list[URLImportResult]:
#         match = strict_re.strict_match(self._url_regex(), url)
#         source_name = match.group("source_name")
#         show_key = match.group("show_key")
#         _locale = match.group("locale")  # TODO: Support multiple locales from JustWatch
#         season_key = match.group("season_key")

#         if not (shows := self._preload_show(show_key=show_key).all()):
#             self._preload_show_files(show_key)
#             self.__validate_show_key(show_key, url)
#             self._preload_season_episode_files(show_key)
#             self._preload_all_latest_new_titles_files(show_key)
#             self._download_initial_files(show_key)
#             shows = self.__upsert_sources(show_key)

#         return self.__create_url_import_results(shows, source_name, season_key)

#     def __validate_show_key(self, show_key: str, url: str) -> None:
#         series_json = self._url_title_details_file(show_key)
#         self.raise_if_no_content(series_json, url)

#     def __create_url_import_results(
#         self,
#         shows: Sequence[Show],
#         source_name: str | None,
#         season_key: str | None,
#     ) -> list[URLImportResult]:
#         output: list[URLImportResult] = []
#         # If the user specified a source name get the show for that source only,
#         # otherwise get all shows.
#         filtered_shows = self.__get_best_show(shows, source_name)

#         # If the URL that the user used was for a specific season only return that
#         # season.
#         if season_key:
#             # The season.id value in the database is the internal one used by JustWatch,
#             # but the user's input will be the external one used by JustWatch so the
#             # easiest way to match a season is by using the actual season number. This
#             # is probably reliable.
#             season_number = int(season_key.split("-")[-1])
#             for show in filtered_shows:
#                 season = next(
#                     (
#                         season
#                         for season in show.seasons
#                         if season.season_number == season_number
#                     ),
#                 )
#                 # If the source has no episodes for this season it should not be
#                 # included..
#                 if not season.episodes:
#                     continue

#                 single_import_result = URLImportResult(
#                     show=show,
#                     seasons=[season],
#                     whitelist_mode=True,
#                 )
#                 output.append(single_import_result)
#             return output

#         for show in filtered_shows:
#             single_import_result = URLImportResult(show=show, whitelist_mode=False)
#             output.append(single_import_result)

#         return output

#     def __get_best_show(
#         self,
#         shows: Sequence[Show],
#         source_name: str | None,
#     ) -> Sequence[Show]:
#         """Filters shows based on the closest match to the given source name.

#         Returns:
#         - If source_name is None or empty, all shows are returned.
#         - If source_name is a valid string, the show with the closest matching name is
#         returned.
#         """
#         if not source_name:
#             return shows

#         source_name = source_name.lower()
#         sources = {show.source.name.lower(): show for show in shows}
#         source_matches = get_close_matches(source_name, sources.keys(), n=1, cutoff=0.0)
#         return [sources[source_matches[0]]]

#     # endregion

#     # region Update Source

#     @override
#     def update_source(self, source: Source) -> None:
#         self._latest_browse_files[source.key] = self._preload_latest_new_titles_file(
#             source.key,
#         )
#         self._download_missing_new_titles_files(source)
#         self._download_outdated_new_titles_files(source)
#         self.__process_new_titles_files(source)

#         latest_browse_file = self._latest_browse_files[source.key]
#         last_update_timestamp = latest_browse_file.get_data_timestamp()
#         source.data_timestamp = last_update_timestamp

#         # You can't just run update_source without a show so it is easier to manually
#         # set the update_at value.
#         source.set_update_at(last_update_timestamp + timedelta(days=1))

#     def __process_new_titles_files(self, source: Source) -> None:
#         # B018 - This preloads the shows into memory so Show.get_from_memory can be
#         # used.
#         source.shows

#         for file in self.__new_titles_files_to_import(source):
#             new_titles_file = self._db_file_to_new_titles_file(file)
#             source_key = new_titles_file.source_key
#             parsed_date = tz_datetime.combine(
#                 new_titles_file.date,
#                 datetime.min.time(),
#             )
#             get_new_titles = self._new_titles_file(source.key, parsed_date)

#             source = Source.get_one(self.db, self.plugin, source_key)
#             for edge in get_new_titles.parsed():
#                 if edge.node.field__typename == "Season":
#                     show_key = edge.node.content.full_path.rsplit("/", 1)[0]
#                     season_key = edge.node.content.full_path.rsplit("/", 1)[1]
#                 elif edge.node.field__typename == "Movie":
#                     show_key = edge.node.content.full_path
#                     season_key = edge.node.content.full_path
#                 else:
#                     msg = f"Unknown field__typename: {edge.node.field__typename}"
#                     raise ValueError(msg)
#                 # Need to match on show because if this is a new season looking up an
#                 # existing season would fail.
#                 if show := Show.get_from_memory(self.db, source, show_key):
#                     # B018 - Preloads all seasons into memory
#                     show.seasons
#                     # If the season was found only the season needs to be updated.
#                     if season := Season.get_from_memory(self.db, show, season_key):
#                         season.set_update_at(get_new_titles.get_data_timestamp())
#                     # If no season was found this contains a new episode so the show
#                     # needs to be updated.
#                     else:
#                         show.set_update_at(get_new_titles.get_data_timestamp())

#             # Only mark a file as imported if the file definitely includes all of the
#             # information for that date.
#             if tz_datetime.now() > parsed_date + timedelta(days=2):
#                 get_new_titles.set_file_extra("Imported")

#     # endregion

#     # region Update

#     @override
#     def update_show(self, show: Show) -> None:
#         show_key = show.key
#         self.__preload_update_media(show_key)
#         for show_file in self._show_files(show_key):
#             show_file.download_if_outdated(show.update_at)
#         self.__upsert_sources(show_key)

#     @override
#     def update_season(self, season: Season) -> None:
#         show_key = season.show.key
#         self.__preload_update_media(show_key)
#         for season_file in self._season_files(show_key, season.key):
#             season_file.download_if_outdated(season.update_at)
#         self.__upsert_sources(show_key)

#     @override
#     def update_episode(self, episode: Episode) -> None:
#         show_key = episode.season.show.key
#         self.__preload_update_media(show_key)
#         for episode_file in self._episode_files(
#             episode.season.key,
#             episode.key,
#             show_key=show_key,
#         ):
#             episode_file.download_if_outdated(episode.update_at)
#         self.__upsert_sources(show_key)

#     # endregion

#     # region Preload

#     def __preload_update_media(self, show_key: str) -> None:
#         self._preload_show(show_key=show_key)
#         self._preload_show_season_episode_files(show_key)
#         # This must be run after _preload_show_season_episode_files because it relies
#         # on those files to determine what sources are used.
#         self._preload_all_latest_new_titles_files(show_key)

#     # endregion

#     # region Regex

#     @classmethod
#     @cache
#     def _url_regex(cls) -> str:
#         # Example URLs:
#         # https://www.justwatch.com/us/tv-show/kaiju-no-8
#         # https://www.justwatch.com/us/tv-show/kaiju-no-8/season-1
#         # https://www.justwatch.com/us/movie/weapons-2026
#         # E501 - Splitting the regex into multiple lines does not make it more readable.
#         url_string = r"(?P<show_key>\/(?P<locale>[a-zA-Z]{2})\/(?:tv-show|movie)\/.+?)(?:\/|$)(?:(?P<season_key>.+?)(?:\/|$))?"
#         source_name_regex = r"^(?P<source_name>.*?)"
#         domain_regex = cls._domain_regex()
#         # Remove the start of string character to support choosing a source by placing
#         # it in front of the URL.
#         domain_regex = domain_regex.replace("^", "", 1)

#         return source_name_regex + domain_regex + url_string

#     # endregion

#     # region Class Methods

#     @classmethod
#     @cache
#     @override
#     def domains(cls) -> list[str]:
#         return ["justwatch.com"]

#     @classmethod
#     @cache
#     def _images_base_url(cls) -> str:
#         return f"https://images.{cls._domain()}"

#     @classmethod
#     def _clean_poster_image_url(cls, url: str) -> str:
#         # 332 is the highest resolution normally used on the website it looks like for
#         # season posters.
#         formatted_url = url.replace("{profile}", "s332").replace("{format}", "avif")
#         return cls._images_base_url() + formatted_url

#     @classmethod
#     def _clean_favicon_image_url(cls, url: str) -> str:
#         formatted_url = url.replace("{format}", "jpeg")
#         return cls._images_base_url() + formatted_url

#     # endregion

#     # region Upsert

#     def __upsert_sources(self, show_key: str) -> list[Show]:
#         """Upsert all sources and their shows from the URL title details JSON."""
#         logger.info(
#             f"Upserting: {self._pretty_show_name(show_key)} ({self._media_type(show_key)})",
#         )
#         source_dict_lookup = {source.key: source for source in self.plugin.sources}
#         shows: list[Show] = []
#         for source_key, offer in self._sources_with_offers(show_key):
#             latest_browse_file = self._latest_browse_files[source_key]
#             source = SourceInput(
#                 key=source_key,
#                 name=offer.package.clear_name,
#                 favicon_url=self._clean_favicon_image_url(offer.package.icon),
#                 update_at=latest_browse_file.get_data_timestamp() + timedelta(days=1),
#                 data_timestamp=latest_browse_file.get_data_timestamp(),
#             ).upsert(self.plugin, source_dict_lookup.get(source_key))
#             shows.append(self.__upsert_show(source, offer, show_key))
#         return shows

#     def __upsert_show(
#         self,
#         source: Source,
#         offer: url_title_details_models.Offer,
#         show_key: str,
#     ) -> Show:
#         # Soft delete everything then re-import everything to manage deletions.
#         if existing_show := Show.get_from_memory(self.db, source, show_key):
#             existing_show.soft_delete()

#         json_file = self._url_title_details_file(show_key)
#         parsed_json = json_file.parsed()

#         show = ShowInput(
#             key=show_key,
#             name=parsed_json.data.url_v2.node.content.title,
#             media_type=self._media_type(show_key),
#             description=parsed_json.data.url_v2.node.content.short_description,
#             url=self._clean_external_url(offer.standard_web_url),
#             image_url=self._images_base_url()
#             + parsed_json.data.url_v2.node.content.full_backdrops[0].backdrop_url,
#             data_timestamp=self._show_timestamp(show_key),
#         ).upsert(source, existing_show)
#         self.__upsert_seasons(show, show_key)
#         return show

#     def __upsert_seasons(self, show: Show, show_key: str) -> None:
#         if self._media_type(show_key) == "TV Show":
#             self.__upsert_show_seasons(show, show_key)
#         else:
#             self.__upsert_movie_season(show, show_key)

#     def __upsert_show_seasons(self, show: Show, show_key: str) -> None:
#         # TODO: Upstream in JustScrape, add the ability to parse specific types so there
#         # is less need for checking for None.
#         json_file = self._url_title_details_file(show_key)
#         parsed_json = json_file.parsed()
#         seasons_data = parsed_json.data.url_v2.node.seasons
#         # TODO: Eventually this should be able to be removed once JustScrape is updated.
#         if seasons_data is None:
#             msg = f"No seasons found for show: {show_key}"
#             raise ValueError(msg)
#         for season_data in seasons_data:
#             existing_season = Season.get_from_memory(
#                 self.db,
#                 show,
#                 season_data.id,
#             )
#             season = SeasonInput(
#                 image_url=self._clean_poster_image_url(
#                     season_data.content.poster_url,
#                 ),
#                 # TODO: Should I use the other ID that matches the URL instead?
#                 key=season_data.id,
#                 sort_order=season_data.content.season_number,
#                 season_number=season_data.content.season_number,
#                 data_timestamp=self._season_timestamp(
#                     show_key,
#                     season_data.id,
#                 ),
#             ).upsert(show, existing_season)
#             self.__upsert_season_episodes(show, season, season_data, show_key)

#     def __upsert_movie_season(self, show: Show, show_key: str) -> None:
#         file_content = self._url_title_details_file(show_key)
#         parsed_json = file_content.parsed()
#         node_id = parsed_json.data.url_v2.node.id
#         existing_season = Season.get_from_memory(self.db, show, node_id)
#         season = SeasonInput(
#             key=node_id,
#             name="Movie",
#             sort_order=0,
#             data_timestamp=self._season_timestamp(show_key, node_id),
#         ).upsert(show, existing_season)
#         self.__upsert_movie_episode(show, season, show_key)

#     def __upsert_season_episodes(
#         self,
#         show: Show,
#         season: Season,
#         season_data: url_title_details_models.Season,
#         show_key: str,
#     ) -> None:
#         source_key = show.source.key
#         custom_season_episodes_file = self._custom_season_episodes_file(
#             season_data.id,
#         )
#         custom_season_episodes_data = custom_season_episodes_file.parsed()
#         for i, season_episode in enumerate(custom_season_episodes_data):
#             buy_box_offers = self._custom_buy_box_offers_file(season_episode.id)
#             episode_info = self._find_matching_episode(
#                 source_key,
#                 buy_box_offers.parsed().data.node,
#             )
#             if not episode_info:
#                 continue

#             # For a little bit of variety in the images, rotate through the backdrop
#             # images so every episode doesn't have the same image.
#             backdrops = (
#                 self._url_title_details_file(show_key)
#                 .parsed()
#                 .data.url_v2.node.content.full_backdrops
#             )
#             backdrop_image = backdrops[i % len(backdrops)].backdrop_url

#             existing_episode = Episode.get_from_memory(
#                 self.db,
#                 season,
#                 season_episode.id,
#             )

#             EpisodeInput(
#                 url=self._clean_external_url(episode_info.standard_web_url),
#                 key=season_episode.id,
#                 name=season_episode.content.title,
#                 description=season_episode.content.short_description,
#                 duration=season_episode.content.runtime * 60,
#                 sort_order=season_episode.content.episode_number,
#                 episode_number=season_episode.content.episode_number,
#                 data_timestamp=self._episode_timestamp(season.key, season_episode.id),
#                 image_url=self._images_base_url() + backdrop_image,
#                 release_date=season_episode.content.original_release_date,
#                 air_date=season_episode.content.original_release_date,
#             ).upsert(season, existing_episode)

#     def __upsert_movie_episode(self, show: Show, season: Season, show_key: str) -> None:
#         source_key = show.source.key
#         episode_info = self._find_matching_episode(
#             source_key,
#             self._url_title_details_file(show_key).parsed().data.url_v2.node,
#         )
#         if not episode_info:
#             return

#         url_title_details_file = self._url_title_details_file(show_key)
#         url_title_details_data = url_title_details_file.parsed()

#         existing_episode = Episode.get_from_memory(
#             self.db,
#             season,
#             episode_info.id,
#         )
#         EpisodeInput(
#             url=self._clean_external_url(episode_info.standard_web_url),
#             key=episode_info.id,
#             name=url_title_details_data.data.url_v2.node.content.title,
#             description=url_title_details_data.data.url_v2.node.content.short_description,
#             duration=url_title_details_data.data.url_v2.node.content.runtime * 60,
#             sort_order=0,
#             episode_number=0,
#             data_timestamp=self._episode_timestamp(
#                 season.key,
#                 episode_info.id,
#             ),
#             release_date=url_title_details_data.data.url_v2.node.content.original_release_date,
#             air_date=url_title_details_data.data.url_v2.node.content.original_release_date,
#         ).upsert(season, existing_episode)

#     def _get_best_episode_date(
#         self,
#         episode_data: UrlTitleDetails,
#     ) -> date | None:
#         """Get the best available date for the episode."""
#         if (
#             release_date
#             := episode_data.parsed().data.url_v2.node.content.original_release_date
#         ):
#             return release_date

#         # When the year is not known a value of 0 is returned for shows, this is
#         # PROBABLY also true for movies. If the value is 0 None is returned.
#         if year := episode_data.parsed().data.url_v2.node.content.original_release_year:
#             return date(year, 1, 1)
#         return None

#     # endregion

#     # region Other

#     @staticmethod
#     def _clean_external_url(url: str) -> str:
#         """Remove affiliate tracking from the episode URL."""
#         parsed_url = urlparse(url)

#         # Used by Crunchyroll and potentially others.
#         if re.compile(r"^https:\/\/[a-z]+\.pxf\.io\/").match(url):
#             query_params = parse_qs(parsed_url.query)
#             if redirect_url := query_params.get("u"):
#                 url = redirect_url[0]
#         return url

#     # TODO: What are FastItem entries?
#     def _find_matching_episode(
#         self,
#         source_key: str,
#         custom_buy_box_offers: custom_buy_box_offers_models.Node,  # | url_title_details_models.Node,
#     ) -> (
#         custom_buy_box_offers_models.FlatrateItem
#         | custom_buy_box_offers_models.BuyItem
#         | custom_buy_box_offers_models.FreeItem
#         | custom_buy_box_offers_models.FastItem
#         # TODO: Enable rent items once the data structure exists.
#         # | custom_buy_box_offers_models.RentItem
#         | None
#     ):
#         # Eventually the types here will no longer have unknown values so the type
#         # errors will go away as JustScrape automatically updates.
#         offers: list[
#             custom_buy_box_offers_models.FlatrateItem
#             | custom_buy_box_offers_models.BuyItem
#             | custom_buy_box_offers_models.FreeItem
#             | custom_buy_box_offers_models.FastItem
#         ] = []
#         if custom_buy_box_offers.flatrate:
#             offers.extend(custom_buy_box_offers.flatrate)

#         if custom_buy_box_offers.buy:
#             offers.extend(custom_buy_box_offers.buy)

#         # if custom_buy_box_offers.rent:
#         #     offers.extend(custom_buy_box_offers.rent)

#         if custom_buy_box_offers.free:
#             offers.extend(custom_buy_box_offers.free)

#         if custom_buy_box_offers.fast:
#             offers.extend(custom_buy_box_offers.fast)

#         for offer in offers:
#             if not offer.package:
#                 msg = "Offer package is None, which shouldn't happen."
#                 raise ValueError(msg)
#             if offer.package.short_name == source_key:
#                 return offer

#         return None

#     def __new_titles_files_to_import(self, source: Source) -> Sequence[File]:
#         latest_files_statement = (
#             select(File)
#             .where(
#                 File.plugin == self.plugin,
#                 # TODO: Index may need to be optimized for like queries.
#                 col(File.key).like(f"{NewTitles.__name__}/{source.key}/%"),
#                 # TODO: Extra probably needs to be set to an index since it is being
#                 # used as a filter.
#                 col(File.extra).is_(None),
#             )
#             .order_by(col(File.data_timestamp).asc())
#         )

#         return self.db.exec(latest_files_statement).all()
