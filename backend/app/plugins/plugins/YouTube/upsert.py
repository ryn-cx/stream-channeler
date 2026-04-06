# TODO: Validate
from datetime import timedelta
from typing import Any, override

from app.episodes.models import Episode
from app.plugins.plugins.YouTube.files import FileMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime


class UpsertMixin(FileMixin, register=False):
    @classmethod
    def _playlist_url(cls, playlist_key: str) -> str:
        return f"{cls._base_url()}playlist?list={playlist_key}"

    def _set_season_update_at(self, season: Season) -> None:
        """Set season update_at based on how recently the latest video was uploaded.

        Takes the difference between the season's data_timestamp and the latest
        video's release date to determine when to next update the season. This
        makes frequently updated playlists checked more often than rarely updated
        playlists. The minimum update interval is 1 day.
        """
        if not season.data_timestamp:
            msg = f"Season {season.key} is missing data_timestamp"
            raise ValueError(msg)

        if not season.episodes:
            season.set_update_at(season.data_timestamp + timedelta(days=36500))
            return

        latest_release_date = max(
            (
                episode.release_date
                for episode in season.episodes
                if episode.release_date
            ),
        )

        if not latest_release_date:
            msg = f"Season {season.key} has no release dates on its episodes"
            raise ValueError(msg)

        if not season.data_timestamp:
            msg = f"Season {season.key} is missing data_timestamp"
            raise ValueError(msg)

        update_delay = season.data_timestamp - latest_release_date
        minimum_update_at = tz_datetime.now() + timedelta(days=1)
        update_at = max(season.data_timestamp + update_delay, minimum_update_at)
        season.set_update_at(update_at)

    # region Upsert

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.db, self.plugin, self.plugin_key())

        data_timestamp = tz_datetime.now()
        if source and source.data_timestamp:
            data_timestamp = source.data_timestamp

        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url="https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png",
            data_timestamp=data_timestamp,
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(
        self,
        source: Source,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> Show:
        show = Show.get_from_memory(self.db, source, show_key)
        show_files = self._show_files(show_key)
        show_timestamp = self._file_timestamp(show_files)

        channel_file = self._channel_by_channel_id_file(show_key)
        channel_data = channel_file.parsed()
        channel_item = channel_data.items[0]

        if force_reimport or not self._is_up_to_date(show, show_timestamp):
            show = Show(
                key=channel_item.id,
                name=channel_item.snippet.title,
                url=f"{self._base_url()}channel/{channel_item.id}",
                media_type="YouTube Channel",
                update_at=channel_file.database_entry.data_timestamp
                + timedelta(days=30),
                data_timestamp=show_timestamp,
                source_id=source.id,
            ).upsert(source, show)

        self._upsert_seasons(show, show_key=show_key, force_reimport=force_reimport)
        return show

    def _upsert_seasons(
        self,
        show: Show,
        *,
        show_key: str = "",
        force_reimport: bool = False,
    ) -> None:
        season_keys = self._season_keys_from_file(show_key)
        show.soft_delete_missing_children(season_keys)
        self._upsert_channel_season(show, show_key, force_reimport=force_reimport)
        self._upsert_playlist_seasons(show, show_key, force_reimport=force_reimport)

    def _upsert_channel_season(
        self,
        show: Show,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        """Upsert the uploads playlist (not included in ChannelPlaylists)."""
        uploads_key = self._get_channel_uploads_playlist_key(show.key)
        season = Season.get_from_memory(self.db, show, uploads_key)
        timestamp = self._file_timestamp(self._season_files(show_key, uploads_key))
        if force_reimport or not self._is_up_to_date(season, timestamp):
            season = Season(
                key=uploads_key,
                name=f"Uploads from {show.name}",
                url=self._playlist_url(uploads_key),
                data_timestamp=timestamp,
                show_id=show.id,
            ).upsert(show, season)
        self._upsert_episodes(season, force_reimport=force_reimport)
        self._set_season_update_at(season)

    def _upsert_playlist_seasons(
        self,
        show: Show,
        show_key: str,
        *,
        force_reimport: bool = False,
    ) -> None:
        """Upsert each playlist from the ChannelPlaylists file."""
        channel_playlists_file = self._channel_playlists_file(show_key)
        for parsed_playlist in channel_playlists_file.parsed().items:
            season = Season.get_from_memory(self.db, show, parsed_playlist.id)
            season_files = self._season_files(show_key, parsed_playlist.id)
            timestamp = self._file_timestamp(season_files)
            if force_reimport or not self._is_up_to_date(season, timestamp):
                season = Season(
                    key=parsed_playlist.id,
                    name=parsed_playlist.snippet.title,
                    url=self._playlist_url(parsed_playlist.id),
                    image_url=self._best_thumbnail_url(
                        parsed_playlist.snippet.thumbnails,
                    ),
                    data_timestamp=timestamp,
                    show_id=show.id,
                ).upsert(show, season)
            self._upsert_episodes(season, force_reimport=force_reimport)
            self._set_season_update_at(season)

    def _upsert_episodes(self, season: Season, *, force_reimport: bool = False) -> None:
        episode_keys = list(reversed(self._episode_keys_from_file(season.key)))
        season.soft_delete_missing_children(episode_keys)

        for sort_order, episode_key in enumerate(episode_keys):
            existing = Episode.get_from_memory(self.db, season, episode_key)
            episode_timestamp = self._file_timestamp(self._episode_files(episode_key))
            if not force_reimport and self._is_up_to_date(existing, episode_timestamp):
                continue

            video_data = self._videos_file(episode_key).parsed()
            video_item = video_data.items[0]
            video_snippet = video_item.snippet

            if duration_timedelta := video_item.content_details.duration:
                duration = int(duration_timedelta.total_seconds())
            else:
                duration = None

            existing = Episode(
                key=video_item.id,
                name=video_snippet.title,
                url=f"{self._base_url()}watch?v={video_item.id}",
                description=video_snippet.description,
                release_date=video_snippet.published_at,
                air_date=video_snippet.published_at,
                duration=duration,
                image_url=self._best_thumbnail_url(video_snippet.thumbnails),
                sort_order=sort_order,
                data_timestamp=self._file_timestamp(self._episode_files(episode_key)),
                season_id=season.id,
            ).upsert(season, existing)

    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None
