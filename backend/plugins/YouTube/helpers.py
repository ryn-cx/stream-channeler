# TODO: Validate
from typing import Any, override
from urllib.parse import quote

from plugins.YouTube.files import FileMixin


class HelperMixin(FileMixin, register=False):
    def record_album_playlist_key(self, playlist_key: str) -> None:
        self._imported_album_playlist_keys.add(playlist_key)

    def _channel_has_only_uploads(self, show_key: str) -> bool:
        channel_playlists_file = self.channel_playlists_file(show_key)
        if not channel_playlists_file.database_record.content:
            return True
        return not any(
            item.content_details.item_count > 0
            for item in channel_playlists_file.parsed().items
        )

    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"results?search_query={quote(query)}")

    @classmethod
    def _playlist_url(cls, playlist_key: str) -> str:
        return cls.build_url(f"playlist?list={playlist_key}")

    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
        # It sounds wrong but standard is a higher resolution than high.
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None
