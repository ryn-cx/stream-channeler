# TODO: Validate
from typing import Any, override
from urllib.parse import quote

from app.media.media_type import MediaType
from app.sources.models import Source
from plugins.YouTube.files import (
    FileMixin,
    is_show_season_key,
    is_video_key,
)


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    # TODO: Validate
    def record_album_playlist_key(self, playlist_key: str) -> None:
        self._importing_album_playlist_key = playlist_key

    # TODO: Validate
    def tmdb_media_type(self, show_key: str) -> MediaType:
        return MediaType.movie if is_video_key(show_key) else MediaType.tv

    # TODO: Validate
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> int | None:
        if not is_show_season_key(season_key):
            return None
        episode_keys = self._season_episode_keys(season_key)
        if episode_key not in episode_keys:
            return None
        return episode_keys.index(episode_key) + 1

    # TODO: Validate
    def _standalone_video_source(self, channel_key: str, channel_name: str) -> Source:
        """Return the `Source` for videos that are imported one video at a time.

        A channel whose videos are imported individually holds licensed titles rather
        than the uploads of a creator, so it gets a `Source` of its own.
        """
        source_key = f"{self.plugin_key()}:{channel_key}"
        # TODO: THIS IS AI BULLSHIT
        # Looked up against the database rather than only the session, because a
        # channel gets a source the first time one of its videos is imported and
        # nothing loads that source into a later session before this reads it.
        source = Source.get(self.session, self.plugin, source_key)
        return Source(
            key=source_key,
            name=channel_name,
            favicon_url=self.FAVICON_URL,
            data_timestamp=self._existing_data_timestamp_or_now(source),
            plugin_id=self.plugin.id,
        ).upsert_and_set_update_at(self.plugin, source)

    # TODO: Validate
    def _channel_has_only_uploads(self, show_key: str) -> bool:
        channel_playlists_file = self.channel_playlists_file(show_key)
        if not channel_playlists_file.database_record.content:
            return True
        return not any(
            item.content_details.item_count > 0
            for item in channel_playlists_file.parsed().items
        )

    # TODO: Validate
    @override
    @classmethod
    def search_url(cls, query: str) -> str | None:
        return cls.build_url(f"results?search_query={quote(query)}")

    # TODO: Validate
    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
        # It sounds wrong but standard is a higher resolution than high.
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None
