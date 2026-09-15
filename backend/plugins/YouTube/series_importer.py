# TODO: Validate
# from __future__ import annotations

# from datetime import timedelta
# from typing import TYPE_CHECKING, Any, override

# from app.seasons.models import Season
# from app.titles.models import Title
# from plugins.YouTube.licensed_importer import YouTubeLicensedMediaImporter
# from plugins.YouTube.utils import (
#     split_title_season_key,
#     title_season_key,
#     title_season_numbers_from_file,
#     title_season_url,
#     title_url,
# )

# if TYPE_CHECKING:
#     from collections.abc import Sequence

#     from app.sources.models import Source
#     from plugins.utils.base_plugin.files import BaseFile


# # TODO: Validate
# class YouTubeTVShowImporter(YouTubeLicensedMediaImporter):
#     # TODO: Validate
#     @override
#     def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
#         # A title has no API of its own, so its listing lists its seasons.
#         return [self.browse_file(title_key)]

#     # TODO: Validate
#     @override
#     def _season_files(
#         self,
#         season_key: str,
#         title_key: str,
#     ) -> Sequence[BaseFile[Any]]:
#         # A season of a title is described by the page for that season.
#         title_key, _ = split_title_season_key(season_key)
#         return [self.browse_file(title_key)]

#     # TODO: Validate
#     @override
#     def _season_keys_from_title_files(self, title_key: str) -> list[str]:
#         # A title has one season for every season its page lists.
#         return [
#             title_season_key(title_key, season_number)
#             for season_number in title_season_numbers_from_file(
#                 self.browse_file(title_key),
#             )
#         ]

#     # TODO: Validate
#     @override
#     def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
#         title_key, season_number = split_title_season_key(season_key)
#         episode_keys = self.browse_file(title_key).episode_keys_by_season()
#         return episode_keys.get(int(season_number), [])

#     # TODO: Validate
#     @override
#     def _get_episode_number(
#         self,
#         episode_key: str,
#         season_key: str,
#         title_key: str,
#     ) -> int | None:
#         return self._episode_number_from_file_order(episode_key, season_key)

#     # TODO: Validate
#     @override
#     def _upsert_title(
#         self,
#         source: Source,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> Title:
#         title_listing = self.browse_file(title_key)
#         source = self.paid_or_free_source(title_key)

#         title = Title.get_from_memory(self.session, source, title_key)
#         if self._title_is_outdated(title, force=force):
#             data_timestamps = self._title_files_data_timestamps(title_key)
#             title = Title(
#                 key=title_key,
#                 name=title_listing.title_name(),
#                 url=title_url(title_key),
#                 media_type="Series",
#                 data_timestamp=max(data_timestamps),
#                 # A title only changes when a season is added to it.
#                 update_at=min(data_timestamps) + timedelta(days=7),
#                 source_id=source.id,
#             ).upsert(source, title)
#             title.set_update_at(None)

#         self._upsert_seasons(title, title_key, force=force)
#         self._soft_delete_missing_seasons_and_episodes(title_key)

#         return title

#     # TODO: Validate
#     def _upsert_seasons(
#         self,
#         title: Title,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> None:
#         for season_key in self._season_keys_from_title_files(title_key):
#             _, season_number = split_title_season_key(season_key)
#             season = Season.get_from_memory(self.session, title, season_key)
#             if self._season_is_outdated(season, title_key, force=force):
#                 data_timestamps = self._season_files_data_timestamps(
#                     season_key,
#                     title_key,
#                 )
#                 season = Season(
#                     key=season_key,
#                     name=f"Season {season_number}",
#                     season_number=int(season_number),
#                     url=title_season_url(title_key, season_number),
#                     data_timestamp=max(data_timestamps),
#                     # A title only changes when a season or an episode is added
#                     # to it.
#                     update_at=min(data_timestamps) + timedelta(days=7),
#                     title_id=title.id,
#                 ).upsert(title, season)
#                 season.set_update_at(None)
#             self._upsert_episodes(season, title_key, force=force)
