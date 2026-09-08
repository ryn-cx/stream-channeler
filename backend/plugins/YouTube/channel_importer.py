# TODO: Validate
from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Any, override

from app.titles.models import Title
from app.utils import tz_datetime
from plugins.YouTube.music_importer import YouTubeMusicSeasons
from plugins.YouTube.user_importer import YouTubeUserImporter
from plugins.YouTube.utils import (
    channel_uploads_playlist_key,
    channel_url,
    get_first_item,
    image_url,
    is_an_album,
    thumbnail_url,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.seasons.models import Season
    from app.sources.models import Source
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class YouTubeChannelImporter(
    YouTubeUserImporter,
    YouTubeMusicSeasons,
):
    # TODO: Validate
    def _channel_has_only_uploads(self, title_key: str) -> bool:
        channel_playlists_file = self.channel_playlists_file(title_key)
        if not channel_playlists_file.database_record.content:
            return True
        return not any(
            item.content_details.item_count > 0
            for item in channel_playlists_file.parsed().items
        )

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            # Required to detect new seasons (playlists).
            self.channel_playlists_file(title_key),
            # ChannelByHandle is only used to get ChannelByChannelId so it is not used.
            # Required to detect changes to the title (channel).
            self.channel_by_channel_id_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if is_an_album(season_key):
            return [self.music_playlist_file(season_key)]
        return [
            # Required to detect new episodes (videos). Must stay first because
            # season_data_timestamp reads files[0].
            self.playlist_items_file(season_key),
            # Required to detect changes to the season (playlist).
            self.channel_playlists_file(title_key),
        ]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        channel_item = get_first_item(
            self.channel_by_channel_id_file(title_key).parsed().items,
        )
        season_keys: list[str] = []

        # If the channel has uploads also include that as a season. Generally, most
        # playlists consist of uploads from the channel so the channel should be the
        # first season_key listed so when the episodes are downloaded the channel
        # uploads are downloaded first because that will maximize the batch sizes and
        # minimize the number of API calls.
        if int(channel_item.statistics.video_count) > 0:
            season_keys.append(channel_uploads_playlist_key(title_key))

        channel_playlists_file = self.channel_playlists_file(title_key)
        if channel_playlists_file.database_record.content:
            season_keys.extend(
                item.id
                for item in channel_playlists_file.parsed().items
                if item.content_details.item_count > 0
            )

        return self._with_album_seasons(season_keys, title_key)

    # TODO: Validate
    @override
    def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
        if is_an_album(season_key):
            return self.music_playlist_file(season_key).track_keys()
        return self._playlist_items_episode_keys(season_key)

    # TODO: Validate
    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> int | None:
        if not is_an_album(season_key):
            return None
        return self._episode_number_from_file_order(episode_key, season_key)

    # TODO: Validate
    @override
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        if is_an_album(season.key):
            self._upsert_episodes_in_file_order(season, title_key, force=force)
            return
        self._upsert_episodes_from_playlist_items(season, title_key, force=force)

    # TODO: Validate
    @override
    def upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            channel_file = self.channel_by_channel_id_file(title_key)
            channel_item = get_first_item(channel_file.parsed().items)
            data_timestamps = self.title_data_timestamps(title_key)
            title = Title(
                key=channel_item.id,
                name=channel_item.snippet.title,
                url=channel_url(channel_item.id),
                media_type="YouTube Channel",
                # Updating every 30 days is reasonable because this is only used for
                # checking for new playlists and changes to the channel information.
                update_at=channel_file.data_timestamp() + timedelta(days=365),
                data_timestamp=max(data_timestamps),
                canonical_title_validated_at=tz_datetime.now(),
                source_id=source.id,
                image_url=image_url(channel_item.snippet.thumbnails),
                thumbnail_url=thumbnail_url(channel_item.snippet.thumbnails),
            ).upsert(source, title)
            title.set_update_at(None)

        self._upsert_seasons(title, title_key, force=force)
        self._soft_delete_missing(title_key)

        return title

    # TODO: Validate
    def _upsert_seasons(
        self,
        title: Title,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        self._upsert_season_uploads(title, title_key, force=force)
        self._upsert_seasons_playlist(title, title_key, force=force)
        self._upsert_seasons_album(title, title_key, force=force)

    # TODO: Validate
    def _upsert_season_uploads(
        self,
        title: Title,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        channel_item = get_first_item(
            self.channel_by_channel_id_file(title_key).parsed().items,
        )
        if int(channel_item.statistics.video_count) == 0:
            return
        uploads_key = channel_uploads_playlist_key(title.key)
        self._upsert_playlist_season(
            title=title,
            title_key=title_key,
            season_key=uploads_key,
            name=f"Uploads from {title.name}",
            playlist=channel_item,
            force=force,
        )

    # TODO: Validate
    def _upsert_seasons_playlist(
        self,
        title: Title,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        channel_playlists_file = self.channel_playlists_file(title_key)
        if not channel_playlists_file.database_record.content:
            return
        playlists_by_key = {
            parsed_playlist.id: parsed_playlist
            for parsed_playlist in channel_playlists_file.parsed().items
        }
        uploads_key = channel_uploads_playlist_key(title.key)
        for season_key in self._season_keys_from_title_files(title_key):
            if season_key != uploads_key and season_key in playlists_by_key:
                playlist = playlists_by_key[season_key]
                self._upsert_playlist_season(
                    title=title,
                    title_key=title_key,
                    season_key=season_key,
                    name=playlist.snippet.title,
                    playlist=playlist,
                    force=force,
                )
