# TODO: Validate
from datetime import timedelta
from typing import override

from not_yt_dlapi.channel.models import Item as ChannelItem
from not_yt_dlapi.playlists.models import Item as PlaylistsItem

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from plugins.YouTube.files import (
    get_first_item,
    has_tmdb_entry,
    is_show_key,
    is_show_season_key,
    is_video_key,
    split_show_season_key,
)
from plugins.YouTube.helpers import HelperMixin

# A single video changes far less often than a channel or playlist does.
_VIDEO_UPDATE_INTERVAL = timedelta(days=7)
# A show only changes when a season or an episode is added to it.
_SERIES_UPDATE_INTERVAL = timedelta(days=7)


class UpsertMixin(HelperMixin, register=False):
    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if is_video_key(show_key):
            return self._upsert_movie_show(show_key, force=force)
        if is_show_key(show_key):
            return self._upsert_series_show(show_key, force=force)
        return self._upsert_channel_show(source, show_key, force=force)

    def _upsert_series_show(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show_page = self.show_page_file(show_key)
        # Every episode belongs to the same channel the movies do, so a show is
        # imported into the same source they are.
        first_episode = get_first_item(self.show_episode_keys(show_key))
        video_item = get_first_item(self.videos_file(first_episode).parsed().items)
        source = self._standalone_video_source(
            video_item.snippet.channel_id,
            video_item.snippet.channel_title,
        )

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=show_page.title(),
                url=self.build_url(f"show/{show_key}"),
                media_type="YouTube Show",
                data_timestamp=data_timestamp,
                # A show only changes when a season is added to it.
                update_at=data_timestamp + _SERIES_UPDATE_INTERVAL,
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(new_show, source, show, show_key, "tv")

        self._upsert_series_seasons(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _upsert_series_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for season_key in self._season_keys_from_file(show_key):
            _, season_number = split_show_season_key(season_key)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show_key, force=force):
                data_timestamp = self.season_data_timestamp(season_key, show_key)
                new_season = Season(
                    key=season_key,
                    name=f"Season {season_number}",
                    season_number=int(season_number),
                    url=self.build_url(f"show/{show_key}?season={season_number}"),
                    data_timestamp=data_timestamp,
                    update_at=data_timestamp + _SERIES_UPDATE_INTERVAL,
                    show_id=show.id,
                )
                season = self._merge_and_upsert_season(
                    new_season,
                    show,
                    season,
                    show_key,
                    "tv",
                )
            self._upsert_episodes(season, show_key, force=force)

    def _upsert_channel_show(
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
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
                data_timestamp=self.show_data_timestamp(show_key),
                source_id=source.id,
                image_url=self._best_thumbnail_url(channel_item.snippet.thumbnails),
            ).upsert_and_set_update_at(source, show, show_files)

        self._upsert_seasons(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _upsert_movie_show(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        video_item = get_first_item(self.videos_file(show_key).parsed().items)
        source = self._standalone_video_source(
            video_item.snippet.channel_id,
            video_item.snippet.channel_title,
        )

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamp = self.show_data_timestamp(show_key)
            new_show = Show(
                key=show_key,
                name=video_item.snippet.title,
                # A YouTube video with a null character in the description caused
                # importing to hang so it needs to be stripped out.
                description=video_item.snippet.description.replace("\x00", ""),
                url=self.build_url(f"watch?v={show_key}"),
                media_type="YouTube Video",
                image_url=self._best_thumbnail_url(video_item.snippet.thumbnails),
                data_timestamp=data_timestamp,
                # Movies are only updated once a year to make sure they are still
                # available.
                update_at=data_timestamp + timedelta(days=365),
                source_id=source.id,
            )
            show = self._merge_and_upsert_show(
                new_show,
                source,
                show,
                show_key,
                "movie",
            )

        self._upsert_movie_season(show, show_key, force=force)
        self._soft_delete_missing(show_key)

        return show

    def _upsert_movie_season(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, show, show_key)
        if self._season_is_outdated(season, show_key, force=force):
            video_item = get_first_item(self.videos_file(show_key).parsed().items)
            data_timestamp = self.season_data_timestamp(show_key, show_key)
            new_season = Season(
                key=show_key,
                name=video_item.snippet.title,
                url=self.build_url(f"watch?v={show_key}"),
                image_url=self._best_thumbnail_url(video_item.snippet.thumbnails),
                data_timestamp=data_timestamp,
                update_at=data_timestamp,
                show_id=show.id,
            )
            season = self._merge_and_upsert_season(
                new_season,
                show,
                season,
                show_key,
                "movie",
            )
        self._upsert_episodes(season, show_key, force=force)

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
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show_key, force=force):
            season_files = self._season_files(season_key, show_key)
            data_timestamp = self.season_data_timestamp(season_key, show_key)
            season = Season(
                key=season_key,
                name=name,
                url=self.build_url(f"playlist?list={season_key}"),
                image_url=self._best_thumbnail_url(playlist.snippet.thumbnails),
                data_timestamp=data_timestamp,
                update_at=data_timestamp + timedelta(hours=6),
                show_id=show.id,
            ).upsert_and_set_update_at(show, season, season_files)
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
        # A season that is a single video holds only that video.
        if is_video_key(season.key):
            self._upsert_episode(season, show_key, season.key, 0, force=force)
            return

        # A season of a show holds the episodes its page lists, in page order.
        if is_show_season_key(season.key):
            episode_keys = self._season_episode_keys(season.key)
            for position, episode_key in enumerate(episode_keys):
                self._upsert_episode(
                    season,
                    show_key,
                    episode_key,
                    position,
                    force=force,
                )
            return

        seen: set[str] = set()
        for item in self.playlist_items_file(season.key).parsed().items:
            episode_key = item.content_details.video_id
            if not self._video_is_valid(item.snippet.title) or episode_key in seen:
                continue
            seen.add(episode_key)
            self._upsert_episode(
                season,
                show_key,
                episode_key,
                item.snippet.position,
                force=force,
            )

    def _upsert_episode(
        self,
        season: Season,
        show_key: str,
        episode_key: str,
        sort_order: int | None,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, episode_key)
        if not self._episode_is_outdated(episode, season.key, show_key, force=force):
            return

        video_item = get_first_item(self.videos_file(episode_key).parsed().items)
        video_snippet = video_item.snippet

        duration_timedelta = video_item.content_details.duration
        duration = None
        if duration_timedelta:
            duration = int(duration_timedelta.total_seconds())

        new_episode = Episode(
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
            sort_order=sort_order,
            episode_number=self._get_episode_number(episode_key, season.key, show_key),
            episode_identifier=f"{self.plugin_key()} {video_item.id}",
            data_timestamp=self.episode_data_timestamp(
                episode_key,
                season.key,
                show_key,
            ),
            season_id=season.id,
        )

        # Only a movie or a show has a TMDB entry to cross reference against.
        if not has_tmdb_entry(show_key):
            episode_files = self._episode_files(episode_key, season.key, show_key)
            new_episode.upsert_and_set_update_at(season, episode, episode_files)
            return

        self._merge_and_upsert_episode(
            new_episode,
            season,
            episode,
            show_key,
            self._tmdb_media_type(show_key),
        )
