# TODO: Validate
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
