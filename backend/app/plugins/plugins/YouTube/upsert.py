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

    # region Upsert

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())

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
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        existing_show = Show.get_from_memory(self.session, source, show_key)
        channel_file = self._channel_by_channel_id_file(show_key)
        channel_item = channel_file.parsed().items[0]

        show = Show(
            key=channel_item.id,
            name=channel_item.snippet.title,
            url=f"{self._base_url()}channel/{channel_item.id}",
            media_type="YouTube Channel",
            # Updating every 30 days is reasonable because this is only sued for
            # checking if information on the channel itself has changed.
            update_at=channel_file.database_record.data_timestamp + timedelta(days=30),
            data_timestamp=self.show_data_timestamp(show_key),
            source_id=source.id,
        ).upsert(source, existing_show)

        self._upsert_seasons(show, show_key)

        return show

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        self._upsert_channel_season(show, show_key)
        self._upsert_playlist_seasons(show, show_key)
        self.soft_delete_missing_seasons(show_key)

    def _upsert_channel_season(self, show: Show, show_key: str) -> None:
        """Upsert the uploads playlist."""
        channel_item = self._channel_by_channel_id_file(show_key).parsed().items[0]
        if int(channel_item.statistics.video_count) == 0:
            return
        uploads_key = self._get_channel_uploads_playlist_key(show.key)
        season_timestamp = self.season_data_timestamp(uploads_key, show_key)
        season = Season.get_from_memory(self.session, show, uploads_key)
        if not season or season.data_timestamp != season_timestamp:
            season = Season(
                key=uploads_key,
                name=f"Uploads from {show.name}",
                url=self._playlist_url(uploads_key),
                data_timestamp=season_timestamp,
                show_id=show.id,
            ).upsert(show, season)
        self._upsert_episodes(season, show_key)
        self._set_season_update_at(season)

    def _upsert_playlist_seasons(self, show: Show, show_key: str) -> None:
        """Upsert each playlist from the ChannelPlaylists file."""
        uploads_key = self._get_channel_uploads_playlist_key(show.key)
        playlist_season_keys = [
            key for key in self._season_keys_from_file(show_key) if key != uploads_key
        ]
        if not playlist_season_keys:
            return
        playlists_by_key = {
            parsed_playlist.id: parsed_playlist
            for parsed_playlist in self._channel_playlists_file(show_key).parsed().items
        }
        for season_key in playlist_season_keys:
            parsed_playlist = playlists_by_key[season_key]
            season_timestamp = self.season_data_timestamp(season_key, show_key)
            season = Season.get_from_memory(self.session, show, season_key)
            if not season or season.data_timestamp != season_timestamp:
                season = Season(
                    key=season_key,
                    name=parsed_playlist.snippet.title,
                    url=self._playlist_url(season_key),
                    image_url=self._best_thumbnail_url(
                        parsed_playlist.snippet.thumbnails,
                    ),
                    data_timestamp=season_timestamp,
                    show_id=show.id,
                ).upsert(show, season)
            self._upsert_episodes(season, show_key)
            self._set_season_update_at(season)

    def _upsert_episodes(self, season: Season, show_key: str) -> None:
        episode_keys = list(reversed(self._episode_keys_from_file(season.key)))
        # Loop through episode keys because duplicate and invalid videos have already
        # been removed.
        for sort_order, episode_key in enumerate(episode_keys):
            existing_episode = Episode.get_from_memory(
                self.session,
                season,
                episode_key,
            )
            episode_timestamp = self.episode_data_timestamp(
                episode_key,
                season.key,
                show_key,
            )
            if (
                existing_episode
                and existing_episode.data_timestamp == episode_timestamp
            ):
                continue

            video_data = self._videos_file(episode_key).parsed()
            video_item = video_data.items[0]
            video_snippet = video_item.snippet

            duration = None
            if duration_timedelta := video_item.content_details.duration:
                duration = int(duration_timedelta.total_seconds())

            Episode(
                key=video_item.id,
                name=video_snippet.title,
                url=f"{self._base_url()}watch?v={video_item.id}",
                description=video_snippet.description,
                release_date=video_snippet.published_at,
                air_date=video_snippet.published_at,
                duration=duration,
                image_url=self._best_thumbnail_url(video_snippet.thumbnails),
                sort_order=sort_order,
                data_timestamp=episode_timestamp,
                season_id=season.id,
            ).upsert(season, existing_episode)
        self.soft_delete_missing_episodes(season.key)

    # endregion Upsert

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

        if not (active_episodes := season.active_episodes):
            season.set_update_at(season.data_timestamp + timedelta(days=36500))
            return

        latest_release_date = max(
            (
                episode.release_date
                for episode in active_episodes
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

    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None
