"""YouTube plugin."""

# TODO: Validate
import re
from datetime import timedelta
from typing import Any, override

from loguru import logger
from not_yt_dlapi.channel.models import Item as ChannelItem
from not_yt_dlapi.playlists.models import Item as PlaylistsItem
from pydantic import BaseModel

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.YouTube.files import FileMixin, get_first_item
from plugins.YouTube.watch_history import WatchHistoryMixin


class ParsedURL(BaseModel):
    """Results of parsing a YouTube URL."""

    show_key: str
    playlist_key: str
    video_key: str | None = None
    is_playlist_import: bool = False


class YouTube(WatchHistoryMixin, FileMixin, register=True):
    """YouTube plugin."""

    _VERSION = "0.0.1"

    @classmethod
    def __long_domain(cls) -> str:
        return "youtube.com"

    @classmethod
    def __short_domain(cls) -> str:
        return "youtu.be"

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [cls.__long_domain(), cls.__short_domain()]

    @override
    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Channel]\n"
            "> `https://www.youtube.com/@jawed`\n"
            "> `https://www.youtube.com/jawed`\n"
            "> `https://www.youtube.com/c/jawed`\n"
            "> `https://www.youtube.com/user/jawed`\n"
            "> `https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A`\n"
            "> [!TIP/Playlist]\n"
            "> `https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`\n"
            "> [!TIP/Video]\n"
            "> `https://www.youtube.com/watch?v=jNQXAC9IVRw`\n"
            "> `https://youtu.be/jNQXAC9IVRw`\n"
            "> `https://www.youtube.com/shorts/jNQXAC9IVRw`\n"
            "> [!TIP/Video in Playlist]\n"
            "> `https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`\n"
            "> `https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`"
        )

    @classmethod
    @override
    def _url_regex(cls) -> str:
        regexes = [
            cls._channel_key_regex(),
            cls._playlist_key_regex(),
            cls._video_key_regex(),
            cls._channel_handle_regex(),
            cls._channel_username_regex(),
        ]
        return "|".join(regexes)

    @classmethod
    def __domain_regex(cls) -> str:
        long = cls._regex_escape_domain(cls.__long_domain())
        short = cls._regex_escape_domain(cls.__short_domain())
        return rf"(?:{long}|{short})"

    @classmethod
    def _channel_handle_regex(cls) -> str:
        # Valid handle URLs:
        #   Click the channel name from a video.
        #     https://www.youtube.com/@jawed
        #   Click tab on channel page.
        #     https://www.youtube.com/@jawed/videos
        #   Click tab on channel page.
        #     https://www.youtube.com/@jawed/featured
        #   TODO: What is this URL from?
        #     https://www.youtube.com/jawed
        #     https://www.youtube.com/c/jawed
        regex_string = r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"
        return cls._regex_escape_domain(cls.__long_domain()) + regex_string

    @classmethod
    def _channel_username_regex(cls) -> str:
        # Valid username URLs:
        #   TODO: What is this URL from?
        #     https://www.youtube.com/user/jawed
        regex_string = r"\/user\/(?P<channel_username>.+?)(?:$|\/)"
        return cls._regex_escape_domain(cls.__long_domain()) + regex_string

    @classmethod
    def _channel_key_regex(cls) -> str:
        # Valid channel URLs:
        #   TODO: What is this URL from?
        #     https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
        regex_string = r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"
        return cls._regex_escape_domain(cls.__long_domain()) + regex_string

    @classmethod
    def _playlist_key_regex(cls) -> str:
        # Valid 32 character playlist URLs:
        #   Click a playlist.
        #     https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh

        # Valid 16 character playlist URLs:
        #   Click a playlist.
        #     https://www.youtube.com/playlist?list=PL374F6CD60916C2C7

        # Auto-generated YouTube Music album playlists:
        #   Click a playlist.
        #     https://www.youtube.com/playlist?list=OLAK5uy_nt1Nw4wT6I7VlzNknxTiIz3hfED0ttO8Q

        regex_string = r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_)[^&]+)"
        return cls._regex_escape_domain(cls.__long_domain()) + regex_string

    @classmethod
    def _playlist_video_key_regex(cls) -> str:
        # Valid 32 character playlist video URLs:
        #   Click a video from a playlist.
        #     https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfS
        #   Right click video -> Copy video URL
        #     https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   Right click video -> Copy video URL at current time
        #     https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh&t=1
        #   Right click video -> Copy video URL at current time -> Get redirected
        #     https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh&t=1s

        # Valid 16 character playlist video URLs:
        #   Click a video from a playlist.
        #     https://www.youtube.com/watch?v=ew5LyM16k8w&list=PL374F6CD60916C2C7
        #   Right click video -> Copy video URL
        #     https://youtu.be/ew5LyM16k8w?list=PL374F6CD60916C2C7
        #   Right click video -> Copy video URL at current time
        #     https://youtu.be/ew5LyM16k8w?list=PL374F6CD60916C2C7&t=1
        #   Right click video -> Copy video URL at current time -> Get redirected
        #     https://www.youtube.com/watch?v=ew5LyM16k8w&list=PL374F6CD60916C2C7&t=1s

        # Auto-generated YouTube Music album playlists:
        #   Right click video -> Copy video URL
        #     https://youtu.be/hCcwCv3G1FQ?list=OLAK5uy_nt1Nw4wT6I7VlzNknxTiIz3hfED0ttO8Q
        regex_string = (
            r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
            r"list=(?P<playlist_key>(?:PL|OLAK5uy_)[^&]+)"
        )
        return cls.__domain_regex() + regex_string

    @classmethod
    def _video_key_regex(cls) -> str:
        # Valid video URLs:
        #   Click a video.
        #     https://www.youtube.com/watch?v=jNQXAC9IVRw
        #   Right click video -> Copy video URL at current time -> Get redirected
        #     https://www.youtube.com/watch?v=jNQXAC9IVRw&t=120s
        #   Click a short.
        #     https://www.youtube.com/shorts/jNQXAC9IVRw
        #   Right click video -> Copy video URL
        #     https://youtu.be/jNQXAC9IVRw
        #   Right click video -> Copy video URL at current time
        #     https://youtu.be/jNQXAC9IVRw?t=120
        long_domain = cls._regex_escape_domain(cls.__long_domain())
        short_domain = cls._regex_escape_domain(cls.__short_domain())
        long_paths = rf"{long_domain}\/(?:watch\?v=|shorts\/)"
        short_path = rf"{short_domain}\/"
        return (
            rf"(?:{long_paths}|{short_path})"
            r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"
        )

    @override
    def _parse_url(self, url: str) -> ParsedURL:
        # _playlist_video_key_regex needs to be checked before _video_key_regex due to
        # regex overlap.
        if match := re.match(self._playlist_video_key_regex(), url):
            return self._parse_playlist_url(
                url=url,
                playlist_key=match.group("playlist_key"),
                video_key=match.group("video_key"),
            )

        if match := re.match(self._playlist_key_regex(), url):
            return self._parse_playlist_url(url, match.group("playlist_key"))

        if match := re.match(self._video_key_regex(), url):
            video_key = match.group("video_key")
            videos_file = self.videos_file(video_key)
            self.raise_if_invalid_file(videos_file, url)
            show_key = videos_file.parsed().items[0].snippet.channel_id
            return ParsedURL(
                show_key=show_key,
                playlist_key=self._get_channel_uploads_playlist_key(show_key),
                video_key=video_key,
            )

        if match := re.match(self._channel_key_regex(), url):
            channel_key = match.group("channel_key")
            self.raise_if_invalid_file(
                self.channel_by_channel_id_file(channel_key),
                url,
            )
            return ParsedURL(
                show_key=channel_key,
                playlist_key=self._get_channel_uploads_playlist_key(channel_key),
            )

        # _channel_username_regex needs to be checked before _channel_handle_regex due
        # to regex overlap.
        if match := re.match(self._channel_username_regex(), url):
            username_file = self.channel_by_username_file(
                match.group("channel_username"),
            )
            self.raise_if_invalid_file(username_file, url)
            show_key = get_first_item(username_file.parsed().items).id
            return ParsedURL(
                show_key=show_key,
                playlist_key=self._get_channel_uploads_playlist_key(show_key),
            )

        if match := re.match(self._channel_handle_regex(), url):
            handle_file = self.channel_by_handle_file(match.group("channel_handle"))
            self.raise_if_invalid_file(handle_file, url)
            show_key = get_first_item(handle_file.parsed().items).id
            return ParsedURL(
                show_key=show_key,
                playlist_key=self._get_channel_uploads_playlist_key(show_key),
            )

        msg = f"Invalid {self.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def _parse_playlist_url(
        self,
        url: str,
        playlist_key: str,
        video_key: str | None = None,
    ) -> ParsedURL:
        playlist_items_file = self.playlist_items_file(playlist_key)
        self.raise_if_invalid_file(playlist_items_file, url)
        first_item = get_first_item(playlist_items_file.parsed().items)
        if self._is_music_playlist_key(playlist_key):
            # Automatically generated music playlists have a
            # first_item.snippet.channel_id value of UCBR8-60-B28hp2BmDPdntcQ which is
            # the official YouTube channel
            # https://www.youtube.com/channel/UCBR8-60-B28hp2BmDPdntcQ
            # first_item.snippet.video_owner_channel_id will link to the YouTube Topic
            # channel which actually owns the playlist.
            show_key = first_item.snippet.video_owner_channel_id
            if not show_key:
                msg = f"Playlist {playlist_key} is missing video_owner_channel_id."
                raise ValueError(msg)
            self._imported_album_playlist_keys.add(playlist_key)
        else:
            show_key = first_item.snippet.channel_id
        return ParsedURL(
            show_key=show_key,
            playlist_key=playlist_key,
            video_key=video_key,
            is_playlist_import=True,
        )

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed = self._parse_url(url)
        show = self._import_show(parsed.show_key, parsed.playlist_key)
        return self._build_import_result(url, show, parsed)

    def _import_show(self, show_key: str, playlist_key: str) -> Show:
        show = self._preload_show(show_key, preload_episodes=True).one_or_none()
        if not show:
            _cache = self._download_show_files_and_children(show_key)
            return self._upsert_show(self.source, show_key)

        if self._playlist_is_missing(show, playlist_key):
            _cache = self._download_show_files_and_children(show, tz_datetime.now())
            return self._upsert_show(self.source, show_key)

        return show

    def _playlist_is_missing(self, show: Show, playlist_key: str) -> bool:
        # If the playlist being checked is the channel uploads playlist it should only
        # be considered missing if the channel has at least one upload.
        if playlist_key == self._get_channel_uploads_playlist_key(show.key):
            channel_by_channel_id = self.channel_by_channel_id_file(show.key)
            channel_item = get_first_item(channel_by_channel_id.parsed().items)
            if int(channel_item.statistics.video_count) == 0:
                return False
        return not Season.get_from_memory(self.session, show, playlist_key)

    def _build_import_result(
        self,
        url: str,
        show: Show,
        parsed: ParsedURL,
    ) -> list[URLImportResult]:
        if parsed.video_key:
            return [
                URLImportResult(
                    show=show,
                    episodes=[
                        episode
                        for season in show.seasons
                        if season.key == parsed.playlist_key
                        for episode in season.episodes
                        if episode.key == parsed.video_key
                    ],
                    is_whitelist=True,
                ),
            ]

        seasons = [
            season for season in show.seasons if season.key == parsed.playlist_key
        ]
        is_whitelist = True
        # TODO: I do not like this if logic and variable name.
        if not parsed.is_playlist_import:
            uploads_key = self._get_channel_uploads_playlist_key(show.key)
            show_season_keys = {season.key for season in show.seasons}
            # If the URL ends with playlists or a channel has no uploads return all
            # of the playlists for the channel.
            if url.endswith("/playlists") or uploads_key not in show_season_keys:
                is_whitelist = False
                seasons = list(show.seasons)

        return [
            URLImportResult(
                show=show,
                seasons=seasons,
                is_whitelist=is_whitelist,
            ),
        ]

    @classmethod
    def _playlist_url(cls, playlist_key: str) -> str:
        return cls.build_url(f"playlist?list={playlist_key}")

    @staticmethod
    def _best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
        # It sounds wrong but standard is a higher resolution than high.
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None

    def _upsert_source(self) -> Source:
        source = Source.get_from_memory(self.session, self.plugin, self.plugin_key())
        return Source(
            key=self.plugin_key(),
            name=self.plugin_key(),
            # TODO: Don't hardcode the favicon URL
            favicon_url="https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png",
            data_timestamp=self._existing_data_timestamp_or_now(source),
            plugin_id=self.plugin.id,
        ).upsert(self.plugin, source)

    @override
    def _upsert_show(self, source: Source, show_key: str) -> Show:
        if show_check := self._show_chek(source, show_key):
            channel_file = self.channel_by_channel_id_file(show_key)
            channel_item = get_first_item(channel_file.parsed().items)
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
            ).upsert(source, show_check.record)
        else:
            show = show_check.record

        self._upsert_seasons(show, show_key)
        return show

    def _upsert_seasons(self, show: Show, show_key: str) -> None:
        self._upsert_channel_uploads_season(show, show_key)
        self._upsert_playlist_seasons(show, show_key)
        self._upsert_album_seasons(show, show_key)
        self.soft_delete_missing_seasons(show_key)

    def _upsert_season(
        self,
        show: Show,
        show_key: str,
        season_key: str,
        name: str,
        playlist: ChannelItem | PlaylistsItem,
    ) -> None:
        if season_check := self._season_check(show, season_key, show_key):
            season = Season(
                key=season_key,
                name=name,
                url=self._playlist_url(season_key),
                image_url=self._best_thumbnail_url(playlist.snippet.thumbnails),
                data_timestamp=season_check.data_timestamp,
                update_at=season_check.data_timestamp + timedelta(hours=1),
                show_id=show.id,
            ).upsert(show, season_check.record)
        else:
            season = season_check.record
        self._upsert_episodes(season, show_key)

    def _upsert_channel_uploads_season(self, show: Show, show_key: str) -> None:
        channel_item = get_first_item(
            self.channel_by_channel_id_file(show_key).parsed().items,
        )
        if int(channel_item.statistics.video_count) == 0:
            return
        uploads_key = self._get_channel_uploads_playlist_key(show.key)
        self._upsert_season(
            show=show,
            show_key=show_key,
            season_key=uploads_key,
            name=f"Uploads from {show.name}",
            playlist=channel_item,
        )

    def _upsert_album_seasons(self, show: Show, show_key: str) -> None:
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
            )

    def _upsert_playlist_seasons(self, show: Show, show_key: str) -> None:
        channel_playlists_file = self.channel_playlists_file(show_key)
        if not channel_playlists_file.database_record.content:
            return
        playlists_by_key = {
            parsed_playlist.id: parsed_playlist
            for parsed_playlist in channel_playlists_file.parsed().items
        }
        uploads_key = self._get_channel_uploads_playlist_key(show.key)
        for season_key in self._season_keys_from_file(show_key):
            if season_key != uploads_key and season_key in playlists_by_key:
                playlist = playlists_by_key[season_key]
                self._upsert_season(
                    show=show,
                    show_key=show_key,
                    season_key=season_key,
                    name=playlist.snippet.title,
                    playlist=playlist,
                )

    def _upsert_episodes(self, season: Season, show_key: str) -> None:
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
            )
            if not episode_check:
                continue

            video_item = self.videos_file(episode_key).parsed().items[0]
            video_snippet = video_item.snippet

            duration = None
            if duration_timedelta := video_item.content_details.duration:
                duration = int(duration_timedelta.total_seconds())

            Episode(
                key=video_item.id,
                name=video_snippet.title,
                url=self.build_url(f"watch?v={video_item.id}"),
                description=video_snippet.description,
                release_date=video_snippet.published_at,
                air_date=video_snippet.published_at,
                duration=duration,
                image_url=self._best_thumbnail_url(video_snippet.thumbnails),
                sort_order=item.snippet.position,
                data_timestamp=episode_check.data_timestamp,
                season_id=season.id,
            ).upsert(season, episode_check.record)
        self.soft_delete_missing_episodes(season.key)

    @override
    def update_season(self, season: Season) -> None:
        logger.info("Updating season: {}", season.key)
        season = self._preload_season(season.id, preload_show=True).one()
        playlist_feed = self.playlist_feed_file(season.key)
        if playlist_feed.database_record.content:
            old_video_ids = set(playlist_feed.video_ids())
        else:
            old_video_ids: set[str] = set()
        playlist_feed.download_if_outdated(season.update_at)

        # A failed fetch leaves the stored feed untouched, so it is still outdated.
        if playlist_feed.is_outdated(season.update_at):
            logger.warning(
                "PlaylistFeed for season {} is unavailable, skipping new video check.",
                season.key,
            )
            self._preload_and_upsert_show(season.show)
            season.update_at = tz_datetime.now() + timedelta(hours=1)
            return

        new_video_ids = set(playlist_feed.video_ids()) - old_video_ids
        if new_video_ids:
            logger.info(
                "Found {} new videos in season {}: {}",
                len(new_video_ids),
                season.key,
                ", ".join(sorted(new_video_ids)),
            )
            self._download_season_files_and_children(
                season,
                update_at=tz_datetime.now(),
            )
        self._preload_and_upsert_show(season.show)
        season.update_at = playlist_feed.data_timestamp + timedelta(hours=1)

    @override
    def on_update_season_failure(self, season: Season, error: Exception) -> None:
        season.update_at = tz_datetime.now() + timedelta(hours=1)
