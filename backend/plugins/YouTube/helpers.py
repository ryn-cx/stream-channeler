# TODO: Validate
from functools import partial
from typing import Any, override
from urllib.parse import quote

from not_yt_dlapi.exceptions import APIError

from app.media.media_type import MediaType
from app.sources.models import Source
from plugins.YouTube.constants import (
    FREE_SOURCE_KEY,
    LINKS_SOURCE_KEY,
    PAID_SOURCE_KEY,
)
from plugins.YouTube.files import (
    FileMixin,
    is_an_album,
    is_channel_key,
    is_channel_uploads_playlist_key,
    is_show_key,
    is_show_season_key,
    is_video_key,
)


# TODO: Validate
def is_free_movies_channel(channel_key: str) -> bool:
    """Report whether a channel is the one YouTube's free catalogue is published on.

    Everything YouTube serves free with ads is owned by this one channel, and a
    title that has to be bought or rented is owned by a channel generated for
    that title alone, so who owns a video is what says which of the two it is.
    """
    return channel_key == "UCuVPpxrm2VAgpH3Ktln4HXg"


# TODO: Validate
def is_regular_playlist(key: str) -> bool:
    return key.startswith("PL") or is_channel_uploads_playlist_key(key)


# TODO: Validate
def channel_key_from_uploads_playlist_key(key: str) -> str:
    return key[:1] + "C" + key[2:]


# TODO: Validate
def is_quota_error(error: BaseException) -> bool:
    """Report whether `error` is the YouTube API refusing calls until quota resets."""
    if not isinstance(error, APIError):
        return False
    errors = error.error.get("errors", [])
    return any(
        item.get("reason") in frozenset({"dailyLimitExceeded", "quotaExceeded"})
        for item in errors
    )


# TODO: Validate
class HelperMixin(FileMixin, register=False):
    # TODO: Validate
    def record_album_playlist_key(self, playlist_key: str) -> None:
        self._importing_album_playlist_key = playlist_key

    # TODO: Validate
    def record_linking_playlist_key(self, playlist_key: str) -> None:
        self._linking_playlist_key = playlist_key

    # TODO: Validate
    def is_linking_playlist(self, playlist_key: str) -> bool:
        return self._linking_playlist_key == playlist_key

    # TODO: Validate
    @override
    def soft_delete_missing_seasons(self, show_key: str) -> None:
        return

    # TODO: Validate
    @property
    def free_source(self) -> Source:
        return self._source_record(FREE_SOURCE_KEY)

    # TODO: Validate
    @property
    def paid_source(self) -> Source:
        return self._source_record(PAID_SOURCE_KEY)

    # TODO: Validate
    @property
    def links_source(self) -> Source:
        return self._source_record(LINKS_SOURCE_KEY)

    # TODO: Validate
    def show_channel_key(self, show_key: str) -> str | None:
        # A show says nothing about who owns it, so what owns it is read off one of
        # its videos, every one of which is owned by whoever the show is.
        if is_channel_key(show_key):
            return show_key
        if is_video_key(show_key):
            episode_key = show_key
        else:
            episode_keys = self.show_episode_keys(show_key)
            if not episode_keys:
                return None
            episode_key = episode_keys[0]
        items = self.videos_file(episode_key).parsed().items
        return items[0].snippet.channel_id if items else None

    # TODO: Validate
    def is_free_movie(self, show_key: str) -> bool:
        channel_key = self.show_channel_key(show_key)
        return channel_key is not None and is_free_movies_channel(channel_key)

    # TODO: Validate
    def show_channel_title(self, show_key: str) -> str | None:
        episode_keys = self.show_episode_keys(show_key)
        if not episode_keys:
            return None
        items = self.videos_file(episode_keys[0]).parsed().items
        return items[0].snippet.channel_title if items else None

    # TODO: Validate
    def subscription_source(self, show_key: str) -> Source | None:
        if not is_show_key(show_key):
            return None
        if "Try now" not in self.show_listing_file_for_show(show_key).offer_labels():
            return None
        channel_title = self.show_channel_title(show_key)
        if not channel_title:
            return None

        source_key = f"{self.plugin_key()} {channel_title}"
        self._initialize_source(
            source_key,
            partial(self._upsert_source, source_key),
        )
        return self._source_record(source_key)

    # TODO: Validate
    def paid_or_free_source(self, show_key: str) -> Source:
        if subscription := self.subscription_source(show_key):
            return subscription
        if self.is_free_movie(show_key):
            return self.free_source
        return self.paid_source

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
        if not (is_show_season_key(season_key) or is_an_album(season_key)):
            return None
        episode_keys = self._season_episode_keys(season_key)
        if episode_key not in episode_keys:
            return None
        return episode_keys.index(episode_key) + 1

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
    def manual_search(cls, query: str) -> str | None:
        return cls.build_url(f"results?search_query={quote(query)}")

    # TODO: Validate
    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
        # It sounds wrong but standard is a higher resolution than high.
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None
