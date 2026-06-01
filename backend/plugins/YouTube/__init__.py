# TODO: Validate
import json
import re
from datetime import timedelta
from typing import Any, Literal, override

from loguru import logger  # noqa: F401 - TODO: Remove unused import

from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.utils import tz_datetime
from app.watches.schemas import WatchImportResult
from plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from plugins.utils.base_plugin.watch_history import (
    ParsedWatchEntry,
    WatchHistoryMixin,
)
from plugins.YouTube.files import (
    ChannelByChannelId,
    ChannelByHandle,
    ChannelByUsername,
    FileMixin,
    PlaylistItems,
    Videos,
    get_first_item,
)

URLKeyType = Literal[
    "playlist_key",
    "video_key",
    "channel_key",
    "channel_handle",
    "channel_username",
]


class YouTube(WatchHistoryMixin, FileMixin, register=True):
    _VERSION = "0.0.1"
    import_watch_history_file_extension = ".json"

    @override
    def initialize_source(self) -> None:
        if not Source.get_from_memory(self.session, self.plugin, self.plugin_key()):
            self._upsert_source()

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Channel Handle]\n"
            "> `https://www.youtube.com/@jawed`\n\n"
            "> [!TIP/Channel Username]\n"
            "> `https://www.youtube.com/user/jawed`\n\n"
            "> [!TIP/Channel ID]\n"
            "> `https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A`\n\n"
            "> [!TIP/Playlist ID]\n"
            "> `https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`\n\n"
            "> [!TIP/Video]\n"
            "> `https://www.youtube.com/watch?v=jNQXAC9IVRw`"
        )

    @classmethod
    @override
    def import_watch_history_instructions(cls) -> str:
        return (
            "1. Go to [takeout.google.com](https://takeout.google.com)\n"
            "2. Deselect all products, then select only 'YouTube and YouTube Music'\n"
            "3. Click 'All YouTube data included', then select only 'history'\n"
            "4. Choose JSON format (not HTML)\n"
            "5. Export and download the archive\n"
            "6. Extract the archive and find "
            "'watch-history.json'\n"
            "7. Upload that file here"
        )

    @override
    def _parse_watch_history(self, content: str) -> list[ParsedWatchEntry]:
        """Parse YouTube watch history from Google Takeout JSON content."""
        entries = json.loads(content)
        parsed_entries: list[ParsedWatchEntry] = []
        for entry in entries:
            # TODO: Why do some entries have no titleUrl?
            if "titleUrl" not in entry:
                continue
            # Ignore deleted videos
            if "subtitles" not in entry:
                continue

            video_key = entry["titleUrl"].split("=", maxsplit=1)[-1]
            parsed_entries.append(
                ParsedWatchEntry(
                    episode_key=video_key,
                    watch_date=tz_datetime.fromisoformat(entry["time"]),
                    import_result=WatchImportResult(
                        show=entry["subtitles"][0]["name"],
                        show_url=entry["titleUrl"],
                        episode=entry["title"].removeprefix("Watched "),
                        episode_url=entry["titleUrl"],
                    ),
                ),
            )
        return parsed_entries

    @classmethod
    @override
    def parse_url(cls, url: str) -> tuple[URLKeyType, str]:
        if match := re.match(cls.playlist_key_regex(), url):
            return ("playlist_key", match.group("playlist_key"))

        if match := re.match(cls.video_key_regex(), url):
            return ("video_key", match.group("video_key"))

        if match := re.match(cls.channel_key_regex(), url):
            return ("channel_key", match.group("channel_key"))

        if match := re.match(cls.channel_handle_regex(), url):
            return ("channel_handle", match.group("channel_handle"))

        if match := re.match(cls.channel_username_regex(), url):
            return ("channel_username", match.group("channel_username"))

        msg = f"Invalid {cls.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed = self.parse_url(url)
        key_type, key_value = parsed
        self._validate_url(url, key_type, key_value)

        episode_key: str | None = None
        if key_type == "playlist_key":
            playlist_items = self.playlist_items_file(key_value).parsed()
            show_key = playlist_items.items[0].snippet.channel_id
            playlist_key = key_value
        elif key_type == "video_key":
            video_data = self.videos_file(key_value).parsed()
            show_key = get_first_item(video_data.items).snippet.channel_id
            playlist_key = self._get_channel_uploads_playlist_key(show_key)
            episode_key = key_value
        elif key_type == "channel_key":
            show_key = key_value
            playlist_key = self._get_channel_uploads_playlist_key(key_value)
        elif key_type == "channel_handle":
            channel_data = self.channel_by_handle_file(key_value).parsed()
            show_key = get_first_item(channel_data.items).id
            playlist_key = self._get_channel_uploads_playlist_key(show_key)
        else:  # key_type == "channel_username":
            channel_data = self.channel_by_username_file(key_value).parsed()
            show_key = get_first_item(channel_data.items).id
            playlist_key = self._get_channel_uploads_playlist_key(show_key)

        show = self._import_show(show_key, playlist_key)
        return [
            self._build_import_result(
                url,
                show,
                key_type,
                playlist_key,
                episode_key,
            ),
        ]

    def _validate_url(self, url: str, key_type: URLKeyType, key_value: str) -> None:
        file: (
            PlaylistItems
            | ChannelByChannelId
            | ChannelByHandle
            | ChannelByUsername
            | Videos
        )
        if key_type == "playlist_key":
            file = self.playlist_items_file(key_value)
        elif key_type == "video_key":
            file = self.videos_file(key_value)
        elif key_type == "channel_key":
            file = self.channel_by_channel_id_file(key_value)
        elif key_type == "channel_handle":
            file = self.channel_by_handle_file(key_value)
        else:  # key_type == "channel_username"
            file = self.channel_by_username_file(key_value)
        file.download_if_outdated()
        self.raise_invalid_url_if_no_content(file, url)

    def _import_show(self, show_key: str, playlist_key: str) -> Show:
        show = self._preload_show(show_key=show_key, preload_seasons=True).one_or_none()
        if not show:
            _cache = self._download_show_files(show_key)
            source = Source.get_one_from_memory(
                self.session,
                self.plugin,
                self.plugin_key(),
            )
            return self._upsert_show(source, show_key)

        if playlist_key == self._get_channel_uploads_playlist_key(show.key):
            parsed = self.channel_by_channel_id_file(show.key).parsed()
            channel_item = get_first_item(parsed.items)
            if int(channel_item.statistics.video_count) == 0:
                return show

        if not Season.get_from_memory(self.session, show, playlist_key):
            for show_file in self._show_files(show.key):
                show_file.download_if_outdated(tz_datetime.now())
            self._download_show_files(show_key)
            source = Source.get_one_from_memory(
                self.session,
                self.plugin,
                self.plugin_key(),
            )
            return self._upsert_show(source, show_key)

        return show

    def _build_import_result(
        self,
        url: str,
        show: Show,
        key_type: URLKeyType,
        playlist_key: str,
        episode_key: str | None = None,
    ) -> URLImportResult:
        if key_type == "video_key":
            episodes = [
                episode
                for season in show.seasons
                if season.key == playlist_key
                for episode in season.episodes
                if episode.key == episode_key
            ]
            return URLImportResult(
                show=show,
                episodes=episodes,
                is_whitelist=True,
            )

        seasons = [season for season in show.seasons if season.key == playlist_key]
        if key_type != "playlist_key":
            # The user is importing a channel so whitelist new playlists by default.
            is_whitelist = True
            uploads_key = self._get_channel_uploads_playlist_key(show.key)
            show_season_keys = {season.key for season in show.seasons}
            # If the URL ends with playlists or a channel has no uploads return all
            # of the playlists for the channel.
            if url.endswith("/playlists") or uploads_key not in show_season_keys:
                is_whitelist = False
                seasons = list(show.seasons)
        else:
            # The user specifically wants just this playlist so ignore any new
            # playlists.
            is_whitelist = False

        return URLImportResult(
            show=show,
            seasons=seasons,
            is_whitelist=is_whitelist,
        )

    @classmethod
    @override
    def domains(cls) -> list[str]:
        return [cls.__long_domain(), cls.__short_domain()]

    @classmethod
    def __long_domain(cls) -> str:
        return "youtube.com"

    @classmethod
    def __short_domain(cls) -> str:
        return "youtu.be"

    @classmethod
    def channel_handle_regex(cls) -> str:
        # Valid handle URLs:
        #   https://www.youtube.com/@jawed
        #   https://www.youtube.com/@jawed/videos
        #   https://www.youtube.com/@jawed/featured
        regex_string = r"\/@(?P<channel_handle>.+?)(?:$|\/)"
        return cls.__domain_regex() + regex_string

    @classmethod
    def channel_username_regex(cls) -> str:
        # Valid username URLs:
        #   https://www.youtube.com/jawed
        #   https://www.youtube.com/c/jawed
        #   https://www.youtube.com/user/jawed
        regex_string = r"\/(?:c\/|user\/)?(?!@)(?P<channel_username>.+?)(?:$|\/)"
        return cls.__domain_regex() + regex_string

    @classmethod
    def channel_key_regex(cls) -> str:
        # Valid channel URLs:
        #   https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
        #   https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A/videos
        #   https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A/featured
        regex_string = r"\/channel\/(?P<channel_key>UC.{22})(?:$|&|\/)"
        return cls.__domain_regex() + regex_string

    @classmethod
    def playlist_key_regex(cls) -> str:
        # Valid 32 character playlist URLs:
        #   https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   https://youtu.be/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   https://youtu.be/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh

        # Valid 16 character playlist URLs:
        #   https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PL374F6CD60916C2C7
        #   https://www.youtube.com/playlist?list=PL374F6CD60916C2C7
        #   https://youtu.be/watch?v=lVI_J1cbFb4&list=PL374F6CD60916C2C7
        #   https://youtu.be/playlist?list=PL374F6CD60916C2C7
        #   https://youtu.be/lVI_J1cbFb4?list=PL374F6CD60916C2C7

        # Invalid playlist URLs but supported for simplicity:
        #   https://www.youtube.com/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   https://www.youtube.com/lVI_J1cbFb4?list=PL374F6CD60916C2C7

        regex_string = (
            r"\/(?:playlist\?|watch\?v=.{11}&|.{11}\?)list=(?P<playlist_key>PL[^&|^$]+)"
        )
        return cls.__domain_regex() + regex_string

    @classmethod
    def video_key_regex(cls) -> str:
        # Valid video URLs:
        #   https://www.youtube.com/watch?v=jNQXAC9IVRw
        #   https://www.youtube.com/watch?v=jNQXAC9IVRw&t=120s
        #   https://www.youtube.com/shorts/jNQXAC9IVRw
        #   https://youtu.be/jNQXAC9IVRw
        #   https://youtu.be/jNQXAC9IVRw?t=120
        long_domain = cls._escape_domain(cls.__long_domain())
        short_domain = cls._escape_domain(cls.__short_domain())
        long_paths = rf"{long_domain}\/(?:watch\?v=|shorts\/)"
        short_path = rf"{short_domain}\/"
        return (
            rf"(?:{long_paths}|{short_path})"
            r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&/])"
        )

    @classmethod
    @override
    def _url_regex(cls) -> str:
        regexes = [
            cls.channel_key_regex(),
            cls.playlist_key_regex(),
            cls.video_key_regex(),
            cls.channel_handle_regex(),
            cls.channel_username_regex(),
        ]
        return "|".join(regexes)

    @classmethod
    def __domain_regex(cls) -> str:
        long = cls._escape_domain(cls.__long_domain())
        short = cls._escape_domain(cls.__short_domain())
        return rf"(?:{long}|{short})"

    @classmethod
    def _playlist_url(cls, playlist_key: str) -> str:
        return f"{cls._base_url()}playlist?list={playlist_key}"

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
        channel_file = self.channel_by_channel_id_file(show_key)
        channel_item = get_first_item(channel_file.parsed().items)

        show = Show(
            key=channel_item.id,
            name=channel_item.snippet.title,
            url=f"{self._base_url()}channel/{channel_item.id}",
            media_type="YouTube Channel",
            # Updating every 30 days is reasonable because this is only sued for
            # checking if information on the channel itself has changed.
            update_at=channel_file.data_timestamp + timedelta(days=30),
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
        parsed = self.channel_by_channel_id_file(show_key).parsed()
        channel_item = get_first_item(parsed.items)
        if int(channel_item.statistics.video_count) == 0:
            return
        uploads_key = self._get_channel_uploads_playlist_key(show.key)
        season_timestamp = self.season_data_timestamp(uploads_key, show_key)
        season = Season.get_from_memory(self.session, show, uploads_key)
        if (
            not season
            or season.data_timestamp != season_timestamp
            or season.deleted_at is not None
        ):
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
            for parsed_playlist in self.channel_playlists_file(show_key).parsed().items
        }
        for season_key in playlist_season_keys:
            parsed_playlist = playlists_by_key[season_key]
            season_timestamp = self.season_data_timestamp(season_key, show_key)
            season = Season.get_from_memory(self.session, show, season_key)
            if (
                not season
                or season.data_timestamp != season_timestamp
                or season.deleted_at is not None
            ):
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
                and existing_episode.deleted_at is None
            ):
                continue

            video_data = self.videos_file(episode_key).parsed()
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

        if not (active_episodes := season.active_children):
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
    def _best_thumbnail_url(thumbnails: Any) -> str | None:  # noqa: ANN401 - TODO: Add a specific type for thumbnails
        for quality in ("maxres", "standard", "high", "medium", "default"):
            if thumb := getattr(thumbnails, quality, None):
                return thumb.url
        return None
