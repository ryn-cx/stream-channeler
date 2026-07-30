# TODO: Validate
from datetime import timedelta
from typing import override

from not_yt_dlapi.channel.models import Item as ChannelItem
from not_yt_dlapi.playlists.models import Item as PlaylistsItem

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.YouTube.files import get_first_item
from plugins.YouTube.helpers import HelperMixin


class UpsertMixin(HelperMixin, register=False):
    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if show_check := self._show_check(source, show_key, force=force):
            channel_file = self.channel_by_channel_id_file(show_key)
            channel_item = get_first_item(channel_file.parsed().items)
            show_files = self._show_files(show_key)
            show = Show(
                key=channel_item.id,
                name=channel_item.snippet.title,
                url=self.build_url(f"channel/{channel_item.id}"),
                media_type="YouTube Channel",
                # Updating every 30 days is reasonable because this is only used for
                # checking for new playlists and changes to the channel information.
                update_at=channel_file.data_timestamp + timedelta(days=30),
                data_timestamp=show_check.data_timestamp,
                source_id=source.id,
                image_url=self._best_thumbnail_url(channel_item.snippet.thumbnails),
            ).upsert_and_set_update_at(source, show_check.record, show_files)
        else:
            show = show_check.record

        self._upsert_seasons(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _upsert_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        self._upsert_channel_uploads_season(show, show_key, force=force)
        self._upsert_playlist_seasons(show, show_key, force=force)
        self._upsert_album_seasons(show, show_key, force=force)

    def _upsert_season(  # noqa: PLR0913
        self,
        show: Show,
        show_key: str,
        season_key: str,
        name: str,
        playlist: ChannelItem | PlaylistsItem,
        *,
        force: bool = False,
    ) -> None:
        if season_check := self._season_check(show, season_key, show_key, force=force):
            season_files = self._season_files(season_key, show_key)
            season = Season(
                key=season_key,
                name=name,
                url=self._playlist_url(season_key),
                image_url=self._best_thumbnail_url(playlist.snippet.thumbnails),
                data_timestamp=season_check.data_timestamp,
                update_at=season_check.data_timestamp + timedelta(hours=1),
                show_id=show.id,
            ).upsert_and_set_update_at(show, season_check.record, season_files)
        else:
            season = season_check.record
        self._upsert_episodes(season, show_key, force=force)

    def _upsert_channel_uploads_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        channel_item = get_first_item(
            self.channel_by_channel_id_file(show_key).parsed().items,
        )
        if int(channel_item.statistics.video_count) == 0:
            return
        uploads_key = self.channel_uploads_playlist_key(show.key)
        self._upsert_season(
            show=show,
            show_key=show_key,
            season_key=uploads_key,
            name=f"Uploads from {show.name}",
            playlist=channel_item,
            force=force,
        )

    def _upsert_album_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for season_key in self._album_season_keys(show_key):
            playlist = get_first_item(
                self.playlist_info_file(season_key).parsed().items,
            )
            self._upsert_season(
                show=show,
                show_key=show_key,
                season_key=season_key,
                name=playlist.snippet.title,
                playlist=playlist,
                force=force,
            )

    def _upsert_playlist_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        channel_playlists_file = self.channel_playlists_file(show_key)
        if not channel_playlists_file.database_record.content:
            return
        playlists_by_key = {
            parsed_playlist.id: parsed_playlist
            for parsed_playlist in channel_playlists_file.parsed().items
        }
        uploads_key = self.channel_uploads_playlist_key(show.key)
        for season_key in self._season_keys_from_file(show_key):
            if season_key != uploads_key and season_key in playlists_by_key:
                playlist = playlists_by_key[season_key]
                self._upsert_season(
                    show=show,
                    show_key=show_key,
                    season_key=season_key,
                    name=playlist.snippet.title,
                    playlist=playlist,
                    force=force,
                )

    def _upsert_episodes(
        self,
        season: Season,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        seen: set[str] = set()
        for item in self.playlist_items_file(season.key).parsed().items:
            episode_key = item.content_details.video_id
            if not self._video_is_valid(item.snippet.title) or episode_key in seen:
                continue
            seen.add(episode_key)

            episode_check = self._episode_check(
                episode_key,
                season,
                show_key,
                force=force,
            )
            if not episode_check:
                continue

            video_item = self.videos_file(episode_key).parsed().items[0]
            video_snippet = video_item.snippet

            duration_timedelta = video_item.content_details.duration
            duration = None
            if duration_timedelta:
                duration = int(duration_timedelta.total_seconds())

            episode_files = self._episode_files(episode_key, season.key, show_key)
            Episode(
                key=video_item.id,
                name=video_snippet.title,
                url=self.build_url(f"watch?v={video_item.id}"),
                # A YouTube video with a null character in the description caused
                # importing to hang so it needs to be stripped out.
                description=video_snippet.description.replace("\x00", ""),
                release_date=video_snippet.published_at,
                air_date=video_snippet.published_at,
                duration=duration,
                image_url=self._best_thumbnail_url(video_snippet.thumbnails),
                sort_order=item.snippet.position,
                episode_identifier=f"{self.plugin_key()} {video_item.id}",
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert_and_set_update_at(season, episode_check.record, episode_files)
