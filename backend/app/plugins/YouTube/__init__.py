# TODO: Validate
import json
import re
from datetime import timedelta
from functools import cache
from typing import override

from loguru import logger
from not_yt_dlapi.video.models import Snippet

from app.media.models import Episode, EpisodeWatch, Season, Show, Source
from app.media.schemas import (
    EpisodeInput,
    SeasonInput,
    ShowInput,
    SourceInput,
    WatchImportEntry,
    WatchImportFormatInformation,
    WatchImportResult,
)
from app.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.plugins.YouTube.files import ChannelById, ChannelByName, FileMixin, Playlist
from app.users.models import User
from app.utils import tz_datetime


class YouTube(FileMixin, register=True):
    # region Import URL

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        if match := re.match(self.__playlist_id_regex(), url):
            playlist_id = self.__import_playlist_url(url, match)
            whitelist_mode = False
        elif match := re.match(self.__channel_id_regex(), url):
            playlist_id = self.__import_channel_url(url, match)
            whitelist_mode = True
        elif match := re.match(self.__channel_name_regex(), url):
            playlist_id = self.__import_channel_name_url(url, match)
            whitelist_mode = True
        else:
            msg = f"Invalid {self._plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        show = self._preload_show(preload_seasons=True)
        if not show:
            self._preload_show_season_episode_files()
            self._download_initial_files()
            show = self.__upsert_source()
        elif not Season.get_from_memory(self.db, show, playlist_id):
            # This handles the edge case where a user can add the URL to a playlist
            # where the channel is in the database but the playlist is not in the
            # database. When this occurs the show's data needs to be forcefully
            # updated so it includes the new playlist.
            # If this is a channel uploads playlist do not update the files because a
            # channel without uploads will always trigger unnecessary downloads.
            if not playlist_id.startswith("UU"):
                for show_file in self._show_files(show.key):
                    show_file.download_if_outdated(tz_datetime.now())
                self._preload_show_season_episode_files()
                self._download_initial_files()
                show = self.__upsert_source()

        # When importing a channel with no uploads assume the user wants all of the
        # playlists on that channel.
        base_result = URLImportResult(
            show=show,
            seasons=[],
            whitelist_mode=whitelist_mode,
        )

        for season in show.seasons:
            if season.key == playlist_id:
                base_result.seasons = [season]
                break

        return [base_result]

    def __import_playlist_url(self, url: str, match: re.Match[str]) -> str:
        playlist_id = match.group("playlist_id")
        playlist_json = self._playlist_file(playlist_id)
        self._is_valid_url(playlist_json, url)
        self._show_id = playlist_json.parsed().channel_id
        return playlist_id

    def __import_channel_url(self, url: str, match: re.Match[str]) -> str:
        self._show_id = match.group("channel_id")
        channel_json_by_id_file = self._channel_by_id_file(self._show_id)
        self._is_valid_url(channel_json_by_id_file, url)
        return self._get_channel_uploads_playlist_id

    def __import_channel_name_url(self, url: str, match: re.Match[str]) -> str:
        channel_name = match.group("channel_name")
        channel_json_by_name_file = self._channel_by_name_file(channel_name)
        self._is_valid_url(channel_json_by_name_file, url)
        self._show_id = channel_json_by_name_file.parsed().channel_id
        return self._get_channel_uploads_playlist_id

    # endregion Import URL

    # region Update

    @override
    def update_show(self, show: Show) -> None:
        self._show_id = show.key
        self.__preload_update_media()
        for show_file in self._show_files(show.key):
            show_file.download_if_outdated(show.update_at)
        self.__upsert_source()

    @override
    def update_season(self, season: Season) -> None:
        self._show_id = season.show.key
        self.__preload_update_media()
        for season_file in self._season_files(season.key):
            season_file.download_if_outdated(season.update_at)
        self.__upsert_source()

    @override
    def update_episode(self, episode: Episode) -> None:
        self._show_id = episode.season.show.key
        self.__preload_update_media()
        for episode_file in self._episode_files(episode.key):
            episode_file.download_if_outdated(episode.update_at)
        self.__upsert_source()

    def __preload_update_media(self) -> None:
        self._preload_show(preload_episodes=True)
        self._preload_show_season_episode_files()

    # endregion Update

    # region Watch Import

    @classmethod
    @override
    def import_watch_history_info(cls) -> WatchImportFormatInformation:
        return WatchImportFormatInformation(
            plugin_id=cls.plugin_id(),
            plugin_name=cls._plugin_name(),
            file_type="JSON",
            file_extension=".json",
            instructions=(
                "1. Go to [takeout.google.com](https://takeout.google.com)\n"
                "2. Deselect all products, then select only 'YouTube and YouTube Music'\n"
                "3. Click 'All YouTube data included', then select only 'history'\n"
                "4. Choose JSON format (not HTML)\n"
                "5. Export and download the archive\n"
                "6. Extract the archive and find "
                "'watch-history.json'\n"
                "7. Upload that file here"
            ),
        )

    @override
    def import_watch_history(
        self,
        content: str,
        user: User,
        *,
        new_only: bool,
        verified: bool,
    ) -> WatchImportResult:
        """Import YouTube watch history from Google Takeout JSON content."""
        entries = json.loads(content)

        entry_video_ids: list[str] = []
        for entry in entries:
            video_id = entry["titleUrl"].split("=", maxsplit=1)[-1]
            entry_video_ids.append(video_id)

        episodes_on_database = self._get_episodes_by_id(entry_video_ids)
        watched_episode_dates = self._get_watched_episode_dates(
            user,
            episodes_on_database,
        )

        added_watches: list[WatchImportEntry] = []
        skipped_watches: list[WatchImportEntry] = []
        existing_watches: list[WatchImportEntry] = []

        for entry, video_id in zip(entries, entry_video_ids, strict=True):
            # Ignore deleted videos
            if "subtitles" not in entry:
                continue

            import_entry = WatchImportEntry(
                show=entry["subtitles"][0]["name"],
                show_url=entry["titleUrl"],
                episode=entry["title"].removeprefix("Watched "),
                episode_url=entry["titleUrl"],
            )

            if not (episode := episodes_on_database.get(video_id)):
                skipped_watches.append(import_entry)
                continue

            watch_date = tz_datetime.fromisotimestamp(entry["time"])

            watched_dates = watched_episode_dates.setdefault(str(episode.id), [])
            if new_only and watched_dates:
                existing_watches.append(import_entry)
                continue

            if watch_date in watched_dates:
                existing_watches.append(import_entry)
                continue

            self.db.add(
                EpisodeWatch(
                    user_id=user.id,
                    episode_id=episode.id,
                    watch_date=watch_date,
                    verified=verified,
                ),
            )
            watched_dates.append(watch_date)
            added_watches.append(import_entry)

        return WatchImportResult(
            added=added_watches,
            existing=existing_watches,
            skipped=skipped_watches,
        )

    # endregion Watch Import

    # region URL

    @classmethod
    @cache
    @override
    def domains(cls) -> list[str]:
        return [cls.__long_domain(), cls.__short_domain()]

    @classmethod
    @cache
    def __long_domain(cls) -> str:
        return "youtube.com"

    @classmethod
    @cache
    def __short_domain(cls) -> str:
        return "youtu.be"

    @classmethod
    @cache
    def __channel_name_regex(cls) -> str:
        # Example channel URLs:
        #   https://www.youtube.com/jawed - Easily typed URL
        #   https://www.youtube.com/@jawed - While watching a video click the channel
        #   name
        #   https://www.youtube.com/@jawed/videos - From the channel page click a link
        #   to a category on the channel
        #   https://www.youtube.com/@jawed/featured - From the channel page click a link
        #   to a category on the channel
        #   https://www.youtube.com/c/jawed - TODO: Has this url been deprecated?
        regex_string = r"\/(?:@|c\/)?(?P<channel_name>.+?)(?:$|\/)"
        return cls.__long_domain_regex() + regex_string

    @classmethod
    @cache
    def __channel_id_regex(cls) -> str:
        # Example channel URLs:
        #   https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A - While watching a
        #   video click the channel name (for channels without a custom URL)
        #   https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A/videos - From the
        #   channel page click a link to a category on the channel (for channels without
        #   a custom URL)
        regex_string = r"\/channel\/(?P<channel_id>UC.{22})(?:$|&|\/)"
        return cls.__long_domain_regex() + regex_string

    @classmethod
    @cache
    def __playlist_id_regex(cls) -> str:
        # Example playlist URLs:
        #   https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
        #   - From the channel page click a link to a playlist
        #   https://www.youtube.com/playlist?list=PL374F6CD60916C2C7
        #   https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh -
        #   While watching a video in a playlist click the playlist name, note that
        #   playlist length can be 16 or 32.
        #   https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh - While
        #   watching playlist right click the video and hit "Copy video URL"

        # The regex needs to be split in an awkward way to make sure that capture group
        # is not duplicated. Splitting it into 2 makes it a little easier to do that.
        partial_1 = rf"{cls.__long_domain_regex()}\/(?:playlist\?|watch\?v=.{{11}}&)"
        partial_2 = rf"{cls.__short_domain_regex()}\/.{{11}}\?"
        return rf"(?:{partial_1}|{partial_2})list=(?P<playlist_id>PL[^&|^$]+)"

    @classmethod
    @cache
    @override
    def _url_regex(cls) -> str:
        regexes = [
            cls.__channel_id_regex(),
            cls.__playlist_id_regex(),
            cls.__channel_name_regex(),
        ]
        return "|".join(regexes)

    @classmethod
    @cache
    def __long_domain_regex(cls) -> str:
        return cls._escape_domain(cls.__long_domain())

    @classmethod
    @cache
    def __short_domain_regex(cls) -> str:
        return cls._escape_domain(cls.__short_domain())

    # endregion URL

    # region Upsert

    def __upsert_source(self) -> Show:
        logger.info(f"Upserting show: {self._pretty_show_name()}")
        existing_source = Source.get_from_memory(
            self.db,
            self.plugin,
            self._plugin_name(),
        )

        data_timestamp = tz_datetime.now()
        if existing_source:
            data_timestamp = existing_source.data_timestamp

        source = SourceInput(
            key=self._plugin_name(),
            name=self._plugin_name(),
            # TODO: Don't hardcode the favicon URL
            favicon_url="https://www.youtube.com/s/desktop/45ea6c88/img/logos/favicon_144x144.png",
            data_timestamp=data_timestamp,
        ).upsert(self.plugin, existing_source)
        return self.__upsert_show(source)

    def __upsert_show(self, source: Source) -> Show:
        # Soft delete everything then re-import everything to manage deletions.
        if existing_show := Show.get_from_memory(self.db, source, self._show_id):
            existing_show.soft_delete()

        channel_json_by_id = self._channel_by_id_file(self._show_id)
        channel_parsed = channel_json_by_id.parsed()

        show = ShowInput(
            key=channel_parsed.channel_id,
            name=channel_parsed.channel,
            url=channel_parsed.channel_url,
            media_type="YouTube Channel",
            # Channel data isn't that important so only check for changes monthly.
            update_at=channel_json_by_id.get_file_data_timestamp() + timedelta(days=30),
            data_timestamp=self._show_timestamp(channel_parsed.channel_id),
        ).upsert(source, existing_show)
        self.__upsert_seasons(show)
        return show

    def __upsert_seasons(self, show: Show) -> None:
        for season_id in self._season_ids_from_file:
            playlist_videos_file = self._playlist_videos_file(season_id)
            playlist_videos_data = playlist_videos_file.parsed()
            modified_date_str = playlist_videos_data.modified_date
            modified_date = tz_datetime.strptime(modified_date_str, "%Y%m%d").date()
            # Take the difference between the file's data_timestamp and the current time
            # to determine when to next update the season. This will make it so frequently
            # updated playlists are checked more often than rarely updated playlists.
            playlist_date = playlist_videos_file.get_file_data_timestamp().date()
            update_delay = playlist_date - modified_date
            # Update at most once per day.
            minimum_update_at = tz_datetime.now() + timedelta(days=1)
            update_at = max(tz_datetime.now() + update_delay, minimum_update_at)

            existing_season = Season.get_from_memory(self.db, show, season_id)
            season = SeasonInput(
                key=playlist_videos_data.id,
                name=playlist_videos_data.title,
                url=playlist_videos_data.webpage_url,
                image_url=playlist_videos_data.thumbnails[0].url,
                data_timestamp=self._season_timestamp(playlist_videos_data.id),
                update_at=update_at,
            ).upsert(show, existing_season)
            self.__upsert_episodes(season)

    def __upsert_episodes(self, season: Season) -> None:
        playlist_videos_file = self._playlist_videos_file(season.key)
        playlist_videos_data = playlist_videos_file.parsed()

        # Episodes can appear multiple times in the same playlist, but this is
        # intentionally not supported, so instead make sure every episode is only
        # added once per season.
        imported_episode_ids: set[str] = set()
        for i, video in enumerate(reversed(playlist_videos_data.entries)):
            if not self._video_is_valid(video) or video.id in imported_episode_ids:
                continue

            imported_episode_ids.add(video.id)

            video_file = self._video_file(video.id)
            video_data = video_file.parsed()
            video_item = video_data.items[0]
            video_snippet = video_item.snippet

            existing_episode = Episode.get_from_memory(self.db, season, video_item.id)
            EpisodeInput(
                key=video_item.id,
                name=video_snippet.title,
                url=f"{self._base_url()}watch?v={video_item.id}",
                description=video_snippet.description,
                release_date=video_snippet.published_at.date(),
                air_date=video_snippet.published_at.date(),
                duration=int(video_item.content_details.duration.total_seconds()),
                image_url=self.__get_best_image_url(video_snippet),
                sort_order=i,
                data_timestamp=self._episode_timestamp(video_item.id),
            ).upsert(season, existing_episode)

    # endregion Upsert

    def __get_best_image_url(self, snippet: Snippet) -> str:
        if snippet.thumbnails.maxres:
            return snippet.thumbnails.maxres.url

        return snippet.thumbnails.high.url
