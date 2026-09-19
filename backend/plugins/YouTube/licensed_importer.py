# TODO: Validate
# from __future__ import annotations

# from typing import TYPE_CHECKING, override

# from plugins.YouTube.constants import FREE_SOURCE_KEY, PAID_SOURCE_KEY
# from plugins.YouTube.importer import YouTubeImporter
# from plugins.YouTube.shared import (
#     is_channel_key,
#     is_free_movies_channel,
#     is_title_key,
#     is_video_key,
# )

# if TYPE_CHECKING:
#     from app.seasons.models import Season
#     from app.sources.models import Source


# # TODO: Validate
# class YouTubeLicensedMediaImporter(YouTubeImporter):
#     # TODO: Validate
#     @property
#     def free_source(self) -> Source:
#         return self._sources[FREE_SOURCE_KEY]

#     # TODO: Validate
#     @property
#     def paid_source(self) -> Source:
#         return self._sources[PAID_SOURCE_KEY]

#     # TODO: Validate
#     def title_episode_keys_from_files(self, title_key: str) -> list[str]:
#         """Return the episode keys of every season of a title, in season order."""
#         return self._episode_keys_from_season_files(
#             self._season_keys_from_title_files(title_key),
#             title_key,
#         )

#     # TODO: Validate
#     def title_channel_key(self, title_key: str) -> str | None:
#         # A title says nothing about who owns it, so what owns it is read off one of
#         # its videos, every one of which is owned by whoever the title is.
#         if is_channel_key(title_key):
#             return title_key
#         if is_video_key(title_key):
#             episode_key = title_key
#         else:
#             episode_keys = self.title_episode_keys_from_files(title_key)
#             if not episode_keys:
#                 return None
#             episode_key = episode_keys[0]
#         items = self.videos_file(episode_key).parsed().items
#         return items[0].snippet.channel_id if items else None

#     # TODO: Validate
#     def is_free_movie(self, title_key: str) -> bool:
#         channel_key = self.title_channel_key(title_key)
#         return channel_key is not None and is_free_movies_channel(channel_key)

#     # TODO: Validate
#     def title_channel_title(self, title_key: str) -> str | None:
#         episode_keys = self.title_episode_keys_from_files(title_key)
#         if not episode_keys:
#             return None
#         items = self.videos_file(episode_keys[0]).parsed().items
#         return items[0].snippet.channel_title if items else None

#     # TODO: Validate
#     def subscription_source(self, title_key: str) -> Source | None:
#         if not is_title_key(title_key):
#             return None
#         if "Try now" not in self.browse_file(title_key).offer_labels():
#             return None
#         channel_title = self.title_channel_title(title_key)
#         if not channel_title:
#             return None

#         source_key = f"{self.plugin_name()} {channel_title}"
#         return self._upsert_source(source_key)

#     # TODO: Validate
#     def paid_or_free_source(self, title_key: str) -> Source:
#         if subscription := self.subscription_source(title_key):
#             return subscription
#         if self.is_free_movie(title_key):
#             return self.free_source
#         return self.paid_source

#     # TODO: Validate
#     @override
#     def _upsert_episodes(
#         self,
#         season: Season,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> None:
#         self._upsert_episodes_in_file_order(season, title_key)
