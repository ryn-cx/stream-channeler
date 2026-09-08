# TODO: Validate
from __future__ import annotations

from contextlib import suppress
from typing import TYPE_CHECKING, override

from not_yt_dlapi.exceptions import (
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
)

from app.seasons.models import Season
from app.utils import tz_datetime
from plugins.YouTube.importer import YouTubeImporter
from plugins.YouTube.utils import (
    image_url,
    playlist_url,
    thumbnail_url,
    video_is_valid,
)

if TYPE_CHECKING:
    from not_yt_dlapi.channels.models import Item as ChannelItem
    from not_yt_dlapi.playlists.models import Item as PlaylistsItem

    from app.titles.models import Title


# TODO: Validate
class YouTubeUserImporter(YouTubeImporter):
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
                if video_is_valid(item.snippet.title)
            ),
        )

    # TODO: Validate
    @override
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        self._upsert_episodes_from_playlist_items(season, title_key, force=force)

    # TODO: Validate
    def _upsert_playlist_season(  # noqa: PLR0913
        self,
        title: Title,
        title_key: str,
        season_key: str,
        name: str,
        playlist: ChannelItem | PlaylistsItem,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, title, season_key)
        if self._season_is_outdated(season, title_key, force=force):
            data_timestamps = self._season_files_data_timestamps(season_key, title_key)
            season = Season(
                key=season_key,
                name=name,
                url=playlist_url(season_key),
                image_url=image_url(playlist.snippet.thumbnails),
                thumbnail_url=thumbnail_url(playlist.snippet.thumbnails),
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(None)
        self._create_missing_season_feed(season)
        self._upsert_episodes(season, title_key, force=force)

    # TODO: Validate
    def _create_missing_season_feed(self, season: Season) -> None:
        playlist_feed = self.playlist_feed_file(season.key)
        if not playlist_feed.does_not_exist():
            return
        with suppress(ChannelFeedNotFoundError, PlaylistFeedNotFoundError):
            playlist_feed.download_if_outdated(tz_datetime.now())

    # TODO: Validate
    def _upsert_episodes_from_playlist_items(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        seen: set[str] = set()
        for item in self.playlist_items_file(season.key).items():
            episode_key = item.content_details.video_id
            if not video_is_valid(item.snippet.title) or episode_key in seen:
                continue
            self._upsert_episode(
                season,
                title_key,
                episode_key,
                len(seen),
                force=force,
            )
            seen.add(episode_key)
