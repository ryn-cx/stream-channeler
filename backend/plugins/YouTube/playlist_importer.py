# TODO: Validate
# from __future__ import annotations

# from datetime import timedelta
# from typing import TYPE_CHECKING, Any, override

# from app.titles.models import Title
# from plugins.YouTube.constants import LINKS_SOURCE_KEY
# from plugins.YouTube.user_importer import YouTubeUserImporter
# from plugins.YouTube.utils import (
#     get_first_item,
#     image_url,
#     playlist_url,
#     thumbnail_url,
# )

# if TYPE_CHECKING:
#     from collections.abc import Sequence

#     from app.sources.models import Source
#     from plugins.utils.base_plugin.files import BaseFile


# # TODO: Validate
# class YouTubePlaylistImporter(YouTubeUserImporter):
#     # TODO: Validate
#     @property
#     def links_source(self) -> Source:
#         return self._sources[LINKS_SOURCE_KEY]

#     # TODO: Validate
#     @override
#     def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
#         return [self.playlist_info_file(title_key)]

#     # TODO: Validate
#     @override
#     def _season_files(
#         self,
#         season_key: str,
#         title_key: str,
#     ) -> Sequence[BaseFile[Any]]:
#         return [
#             self.playlist_items_file(season_key),
#             self.playlist_info_file(title_key),
#         ]

#     # TODO: Validate
#     @override
#     def _season_keys_from_title_files(self, title_key: str) -> list[str]:
#         return [title_key]

#     # TODO: Validate
#     @override
#     def upsert_title(
#         self,
#         source: Source,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> Title:
#         playlist_item = get_first_item(
#             self.playlist_info_file(title_key).parsed().items,
#         )
#         source = self.links_source

#         title = Title.get_from_memory(self.session, source, title_key)
#         if self._title_is_outdated(title, force=force):
#             data_timestamps = self._title_files_data_timestamps(title_key)
#             title = Title(
#                 key=title_key,
#                 name=playlist_item.snippet.title,
#                 description=playlist_item.snippet.description.replace("\x00", ""),
#                 url=playlist_url(title_key),
#                 media_type="Series",
#                 image_url=image_url(playlist_item.snippet.thumbnails),
#                 thumbnail_url=thumbnail_url(playlist_item.snippet.thumbnails),
#                 data_timestamp=max(data_timestamps),
#                 source_id=source.id,
#             ).upsert(source, title)
#             title.set_update_at(
#                 min(data_timestamps) + timedelta(hours=6),
#             )

#         self._upsert_playlist_season(
#             title=title,
#             title_key=title_key,
#             season_key=title_key,
#             name=playlist_item.snippet.title,
#             playlist=playlist_item,
#             force=force,
#         )
#         self._soft_delete_missing(title_key)

#         return title
