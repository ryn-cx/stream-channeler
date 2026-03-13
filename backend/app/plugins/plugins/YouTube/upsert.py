from datetime import timedelta
from typing import override

from loguru import logger
from not_yt_dlapi.video.models import Snippet

from app.episodes.models import Episode
from app.episodes.schemas import EpisodeInput
from app.plugins.plugins.YouTube.files import FileMixin
from app.seasons.models import Season
from app.seasons.schemas import SeasonInput
from app.shows.models import Show
from app.shows.schemas import ShowInput
from app.sources.models import Source
from app.sources.schemas import SourceInput
from app.utils import tz_datetime


class UpsertMixin(FileMixin, register=False):
    @classmethod
    def _playlist_url(cls, playlist_key: str) -> str:
        return f"{cls._base_url()}playlist?list={playlist_key}"

    # region Upsert

    def _upsert_source(self) -> None:
        source = Source.get_from_memory(self.db, self.plugin, self.plugin_key())

        data_timestamp = tz_datetime.now()
        if source and source.data_timestamp:
            data_timestamp = source.data_timestamp

        source = SourceInput(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url="https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png",
            data_timestamp=data_timestamp,
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
        show_timestamp = self._newest_file_timestamp(show_files)

        channel_json_by_id = self._channel_by_id_file(show_key)
        channel_data = channel_json_by_id.parsed()
        if force_reimport or not show or show.data_timestamp != show_timestamp:
            logger.info(f"Upserting show: {self._pretty_show_name(show_key)}")
            show = ShowInput(
                key=channel_data.channel_id,
                name=channel_data.channel,
                url=channel_data.channel_url,
                media_type="YouTube Channel",
                # Channel data isn't that important so only check for changes monthly.
                update_at=channel_json_by_id.database_entry.data_timestamp
                + timedelta(days=30),
                data_timestamp=show_timestamp,
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

        for season_key in season_keys:
            season = Season.get_from_memory(self.db, show, season_key)
            season_timestamp = self._newest_file_timestamp(
                self._season_files(season_key),
            )
            if (
                force_reimport
                or not season
                or season.data_timestamp != season_timestamp
            ):
                logger.info(f"Upserting season: {season_key}")
                playlist_videos_file = self._playlist_videos_file(season_key)

                # Handle playlists/channels without videos.
                if not playlist_videos_file.database_entry.content:
                    # Channels without uploads will have blank Playlist and PlaylistVideos
                    # files.
                    if season_key == self._get_channel_uploads_playlist_key(show.key):
                        season = SeasonInput(
                            key=self._get_channel_uploads_playlist_key(show.key),
                            name=f"Uploads from {show.name}",
                            url=self._playlist_url(season_key),
                            data_timestamp=season_timestamp,
                        ).upsert(show, season)
                    else:
                        # TODO: Can the name be gotten for playlists without videos as
                        # well?
                        # TODO: Find an empty playlist to test this properly
                        season = SeasonInput(
                            key=season_key,
                            data_timestamp=season_timestamp,
                        ).upsert(show, season)
                else:
                    playlist_videos_data = playlist_videos_file.parsed()
                    modified_date_str = playlist_videos_data.modified_date
                    modified_datetime = tz_datetime.strptime(
                        modified_date_str,
                        "%Y%m%d",
                    )
                    # Take the difference between the file's data_timestamp and the current
                    # time to determine when to next update the season. This will make it so
                    # frequently updated playlists are checked more often than rarely updated
                    # playlists.
                    playlist_datetime = (
                        playlist_videos_file.database_entry.data_timestamp
                    )
                    update_delay = playlist_datetime - modified_datetime
                    # Update at most once per day.
                    minimum_update_at = tz_datetime.now() + timedelta(days=1)
                    update_at = max(tz_datetime.now() + update_delay, minimum_update_at)

                    season = SeasonInput(
                        key=playlist_videos_data.id,
                        name=playlist_videos_data.title,
                        url=playlist_videos_data.webpage_url,
                        image_url=playlist_videos_data.thumbnails[0].url,
                        data_timestamp=season_timestamp,
                        update_at=update_at,
                    ).upsert(show, season)

            self._upsert_episodes(season, force_reimport=force_reimport)

    def _upsert_episodes(self, season: Season, *, force_reimport: bool = False) -> None:
        episode_keys = list(reversed(self._episode_keys_from_file(season.key)))
        season.soft_delete_missing_children(episode_keys)

        for sort_order, episode_key in enumerate(episode_keys):
            existing = Episode.get_from_memory(self.db, season, episode_key)
            if (
                not force_reimport
                and existing
                and existing.data_timestamp
                == self._newest_file_timestamp(self._episode_files(episode_key))
            ):
                continue

            logger.info(f"Upserting episode: {episode_key}")
            video_data = self._video_file(episode_key).parsed()
            video_item = video_data.items[0]
            video_snippet = video_item.snippet

            existing = EpisodeInput(
                key=video_item.id,
                name=video_snippet.title,
                url=f"{self._base_url()}watch?v={video_item.id}",
                description=video_snippet.description,
                release_date=video_snippet.published_at.date(),
                air_date=video_snippet.published_at.date(),
                duration=int(video_item.content_details.duration.total_seconds()),
                image_url=self._get_best_image_url(video_snippet),
                sort_order=sort_order,
                data_timestamp=self._newest_file_timestamp(
                    self._episode_files(episode_key),
                ),
            ).upsert(season, existing)

    def _get_best_image_url(self, snippet: Snippet) -> str:
        if snippet.thumbnails.maxres:
            return snippet.thumbnails.maxres.url

        return snippet.thumbnails.high.url
