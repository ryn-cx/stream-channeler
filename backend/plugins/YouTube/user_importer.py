# TODO: Validate
from __future__ import annotations

from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING, override

from not_yt_dlapi.exceptions import (
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
)

from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.YouTube.importer import YouTubeImporter

if TYPE_CHECKING:
    from not_yt_dlapi.channels.models import Item as ChannelItem
    from not_yt_dlapi.playlist_items.models import Item as PlaylistItemsItem
    from not_yt_dlapi.playlists.models import Item as PlaylistsItem

    from app.titles.models import Title


# TODO: Validate
class YouTubeUserImporter(YouTubeImporter):
    # TODO: Validate
    @override
    def _preload_and_download_files(self, title: Title | str) -> None:
        super()._preload_and_download_files(title)
        title_key = title if isinstance(title, str) else title.key
        for season_key in self._season_keys_from_title_files(title_key):
            self._create_missing_season_feed(season_key)

    # TODO: Validate
    @override
    def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
        return self._playlist_items_episode_keys(season_key)

    # TODO: Validate
    def _playlist_items_episode_keys(self, season_key: str) -> list[str]:
        playlist_items_file = self.playlist_items_file(season_key)
        if not playlist_items_file.record_content:
            msg = (
                f"PlaylistItems file for season {season_key!r} has empty content "
                f"(file key {playlist_items_file.file_key()!r}, extra "
                f"{playlist_items_file.record_extra!r}). The playlist was "
                f"likely not found when downloaded."
            )
            raise ValueError(msg)
        return list(
            dict.fromkeys(
                item.content_details.video_id
                for item in playlist_items_file.items()
                if self.video_is_valid(item.snippet.title)
                and self.video_has_premiered(item)
            ),
        )

    # TODO: Validate
    @staticmethod
    def video_is_valid(video_title: str) -> bool:
        """Check if a video is valid for importing."""
        return video_title not in ("Deleted video", "Private video")

    # TODO: Validate
    @staticmethod
    def video_has_premiered(item: PlaylistItemsItem) -> bool:
        published_at = item.content_details.video_published_at
        return published_at is not None and published_at <= tz_datetime.now()

    # TODO: Validate
    @override
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        self._upsert_episodes_from_playlist_items(season, title_key)

    # TODO: Validate
    def _upsert_playlist_season(
        self,
        title: Title,
        title_key: str,
        season_key: str,
        name: str,
        playlist: ChannelItem | PlaylistsItem,
    ) -> None:
        existing_season = Season.get_from_memory(self.session, title, season_key)
        data_timestamp = self._season_files_data_timestamp(season_key, title_key)
        upserted_season = Season(
            key=season_key,
            name=name,
            url=self.playlist_url(season_key),
            image_url=self.image_url(playlist.snippet.thumbnails),
            thumbnail_url=self.thumbnail_url(playlist.snippet.thumbnails),
            data_timestamp=data_timestamp,
            title_id=title.id,
            update_at=data_timestamp + timedelta(days=1),
        ).upsert(title, existing_season)
        self._upsert_episodes(upserted_season, title_key)

    # TODO: Validate
    def _create_missing_season_feed(self, season_key: str) -> None:
        playlist_feed = self.playlist_feed_file(season_key)
        if not playlist_feed.does_not_exist():
            return
        with suppress(ChannelFeedNotFoundError, PlaylistFeedNotFoundError):
            playlist_feed.download_if_outdated(tz_datetime.now())

    # TODO: Validate
    def _upsert_episodes_from_playlist_items(
        self,
        season: Season,
        title_key: str,
    ) -> None:
        seen: set[str] = set()
        for item in self.playlist_items_file(season.key).items():
            episode_key = item.content_details.video_id
            if (
                not self.video_is_valid(item.snippet.title)
                or not self.video_has_premiered(item)
                or episode_key in seen
            ):
                continue
            self._upsert_episode(
                season,
                title_key,
                episode_key,
                len(seen),
            )
            seen.add(episode_key)
