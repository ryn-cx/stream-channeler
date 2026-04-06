# TODO: Validate
import re
from typing import Literal, override

from app.plugins.plugins.utils.abstract_plugin import InvalidURLError, URLImportResult
from app.plugins.plugins.YouTube.files import (
    ChannelByChannelId,
    ChannelByHandle,
    PlaylistItems,
)
from app.plugins.plugins.YouTube.watch import WatchMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime

URLKeyType = Literal["playlist_key", "channel_key", "channel_name"]


class YouTube(WatchMixin, register=True):
    _VERSION = "0.0.1"

    supports_import_url = True

    @classmethod
    def import_url_instructions(cls) -> str:
        return (
            "> [!TIP/Channel Name]\n"
            "> `https://www.youtube.com/@jawed`\n\n"
            "> [!TIP/Channel ID]\n"
            "> `https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A`\n\n"
            "> [!TIP/Playlist ID]\n"
            "> `https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh`"
        )

    # region Import URL

    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        key_type, key_value = self.__parse_url(url)
        self.__validate_url(url, key_type, key_value)

        if key_type == "playlist_key":
            playlist_items = self._playlist_items_file(key_value).parsed()
            show_key = playlist_items.items[0].snippet.channel_id
            playlist_key = key_value
        elif key_type == "channel_key":
            show_key = key_value
            playlist_key = self._get_channel_uploads_playlist_key(key_value)
        else:
            channel_data = self._channel_by_handle_file(key_value).parsed()
            show_key = channel_data.items[0].id
            playlist_key = self._get_channel_uploads_playlist_key(show_key)

        show = self.__import_show(show_key, playlist_key)
        return [self.__build_import_result(url, show, show_key, key_type, playlist_key)]

    @classmethod
    def __parse_url(cls, url: str) -> tuple[URLKeyType, str]:
        if match := re.match(cls.playlist_key_regex(), url):
            return "playlist_key", match.group("playlist_key")

        if match := re.match(cls.channel_key_regex(), url):
            return "channel_key", match.group("channel_key")

        if match := re.match(cls.channel_name_regex(), url):
            return "channel_name", match.group("channel_name")

        msg = f"Invalid {cls.plugin_key()} URL: {url}"
        raise InvalidURLError(msg)

    def __validate_url(self, url: str, key_type: URLKeyType, key_value: str) -> None:
        """Download and validate that the URL points to real content."""
        file: PlaylistItems | ChannelByChannelId | ChannelByHandle
        if key_type == "playlist_key":
            file = self._playlist_items_file(key_value)
        elif key_type == "channel_key":
            file = self._channel_by_channel_id_file(key_value)
        else:
            file = self._channel_by_handle_file(key_value)
        file.download_if_outdated()
        self.raise_invalid_url_if_no_content(file, url)

    def __import_show(self, show_key: str, playlist_key: str) -> Show:
        show = self._preload_show(show_key=show_key, preload_seasons=True).one_or_none()
        if not show:
            _cache = self._download_show_files(show_key)
            # TODO: Move to initialization
            source = self._upsert_source()
            return self._upsert_show(source, show_key)

        # Handle the edge case where a user adds a playlist that belongs to a channel
        # that is already in the database, but that specific playlist is not in the
        # database.
        if not Season.get_from_memory(self.db, show, playlist_key):
            for show_file in self._show_files(show.key):
                show_file.download_if_outdated(tz_datetime.now())
            self._download_show_files(show_key)
            # TODO: Move to initialization
            source = self._upsert_source()
            return self._upsert_show(source, show_key)

        return show

    def __build_import_result(
        self,
        url: str,
        show: Show,
        show_key: str,
        key_type: URLKeyType,
        playlist_key: str,
    ) -> URLImportResult:
        seasons = [season for season in show.seasons if season.key == playlist_key]
        is_channel = key_type != "playlist_key"

        if is_channel:
            # The user is importing a channel so whitelist new playlists by default.
            whitelist_mode = True
            uploads_key = self._get_channel_uploads_playlist_key(show_key)
            show_season_keys = {season.key for season in show.seasons}
            # If the URL ends with playlists or a channel has no uploads return all
            # of the playlists for the channel.
            if url.endswith("/playlists") or uploads_key not in show_season_keys:
                whitelist_mode = False
                seasons = list(show.seasons)
        else:
            # The user specifically wants just this playlist so ignore any new
            # playlists.
            whitelist_mode = False

        return URLImportResult(
            show=show,
            seasons=seasons,
            whitelist_mode=whitelist_mode,
        )

    # endregion Import URL

    # region URL

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
    def channel_name_regex(cls) -> str:
        # Valid channel URLs:
        #   https://www.youtube.com/jawed
        #   https://www.youtube.com/@jawed
        #   https://www.youtube.com/@jawed/videos
        #   https://www.youtube.com/@jawed/featured
        #   https://www.youtube.com/c/jawed
        regex_string = r"\/(?:@|c\/)?(?P<channel_name>.+?)(?:$|\/)"
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
    @override
    def _url_regex(cls) -> str:
        regexes = [
            cls.channel_key_regex(),
            cls.playlist_key_regex(),
            cls.channel_name_regex(),
        ]
        return "|".join(regexes)

    @classmethod
    def __domain_regex(cls) -> str:
        long = cls._escape_domain(cls.__long_domain())
        short = cls._escape_domain(cls.__short_domain())
        return rf"(?:{long}|{short})"

    # endregion URL
