# TODO: Validate
# from __future__ import annotations

# from datetime import timedelta
# from typing import TYPE_CHECKING, Any, override

# from app.seasons.models import Season
# from app.titles.models import Title
# from plugins.YouTube.licensed_importer import YouTubeLicensedMediaImporter
# from plugins.YouTube.utils import (
#     get_first_item,
#     image_url,
#     thumbnail_url,
#     video_url,
# )

# if TYPE_CHECKING:
#     from collections.abc import Sequence

#     from app.sources.models import Source
#     from plugins.utils.base_plugin.files import BaseFile


# # TODO: Validate
# class YouTubeMovieImporter(YouTubeLicensedMediaImporter):
#     # TODO: Validate
#     @override
#     def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
#         return [self.videos_file(title_key)]

#     # TODO: Validate
#     @override
#     def _season_files(
#         self,
#         season_key: str,
#         title_key: str,
#     ) -> Sequence[BaseFile[Any]]:
#         # A season that is a single video is described by the video itself.
#         return [self.videos_file(season_key)]

#     # TODO: Validate
#     @override
#     def _season_keys_from_title_files(self, title_key: str) -> list[str]:
#         # A title that is a single video has that video as its only season.
#         return [title_key]

#     # TODO: Validate
#     @override
#     def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
#         # A season that is a single video holds only that video.
#         return [season_key]

#     # TODO: Validate
#     @override
#     def upsert_title(
#         self,
#         source: Source,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> Title:
#         video_item = get_first_item(self.videos_file(title_key).parsed().items)
#         source = self.paid_or_free_source(title_key)

#         title = Title.get_from_memory(self.session, source, title_key)
#         if self._title_is_outdated(title, force=force):
#             data_timestamps = self._title_files_data_timestamps(title_key)
#             title = Title(
#                 key=title_key,
#                 name=video_item.snippet.title,
#                 # A YouTube video with a null character in the description caused
#                 # importing to hang so it needs to be stripped out.
#                 description=video_item.snippet.description.replace("\x00", ""),
#                 url=video_url(title_key),
#                 media_type="Movie",
#                 image_url=image_url(video_item.snippet.thumbnails),
#                 thumbnail_url=thumbnail_url(video_item.snippet.thumbnails),
#                 data_timestamp=max(data_timestamps),
#                 # Movies are only updated once a year to make sure they are still
#                 # available.
#                 update_at=min(data_timestamps) + timedelta(days=365),
#                 source_id=source.id,
#             ).upsert(source, title)
#             title.set_update_at(None)

#         self._upsert_season(title, title_key, force=force)
#         self._soft_delete_missing(title_key)

#         return title

#     # TODO: Validate
#     def _upsert_season(
#         self,
#         title: Title,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> None:
#         season = Season.get_from_memory(self.session, title, title_key)
#         if self._season_is_outdated(season, title_key, force=force):
#             video_item = get_first_item(self.videos_file(title_key).parsed().items)
#             data_timestamps = self._season_files_data_timestamps(title_key, title_key)
#             season = Season(
#                 key=title_key,
#                 name=video_item.snippet.title,
#                 image_url=image_url(video_item.snippet.thumbnails),
#                 thumbnail_url=thumbnail_url(video_item.snippet.thumbnails),
#                 data_timestamp=max(data_timestamps),
#                 title_id=title.id,
#             ).upsert(title, season)
#             season.set_update_at(min(data_timestamps))
#         self._upsert_episodes(season, title_key, force=force)
