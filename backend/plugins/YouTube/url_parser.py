# TODO: Validate
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, NamedTuple, override

from plugins.utils.abstract_plugin import InvalidURLError
from plugins.utils.base_plugin.url import ParsedURL
from plugins.YouTube.channel_importer import YouTubeChannelImporter
from plugins.YouTube.files import ChannelByHandle, ChannelByUsername

# from plugins.YouTube.movie_importer import YouTubeMovieImporter
from plugins.YouTube.music_importer import YouTubeMusicImporter
from plugins.YouTube.playlist_importer import YouTubePlaylistImporter

# from plugins.YouTube.series_importer import YouTubeTVShowImporter
from plugins.YouTube.shared import (
    YouTubeShared,
    channel_key_from_uploads_playlist_key,
    channel_uploads_playlist_key,
    get_first_item,
    is_an_album,
    is_channel_uploads_playlist_key,
    is_user_playlist,
)

if TYPE_CHECKING:
    from not_yt_dlapi.channels.models import ChannelsModel

    from plugins.utils.base_plugin.files import BaseFile
    from plugins.YouTube.importer import YouTubeImporter


# TODO: Validate
class YouTubeParsedURL(NamedTuple):
    title_key: str
    playlist_key: str
    video_key: str | None = None
    whole_title: bool = False
    musician_track: bool = False
    album_playlist_key: str | None = None

    # TODO: Validate
    def media_info(self) -> ParsedURL:
        if self.whole_title:
            return ParsedURL(self.title_key)
        if self.video_key is None:
            return ParsedURL(self.title_key, season_key=self.playlist_key)
        # The track is looked for in every release of the musician, since the URL
        if self.musician_track:
            return ParsedURL(self.title_key, episode_key=self.video_key)
        return ParsedURL(
            self.title_key,
            season_key=self.playlist_key,
            episode_key=self.video_key,
        )


# TODO: Validate
class YouTubeURLParserMixin(YouTubeShared):
    # TODO: Validate
    @override
    def _media_importer_from_url(self, url: str) -> YouTubeImporter:
        parsed = self._parsed_url(url)
        if parsed.album_playlist_key:
            importer: YouTubeImporter = YouTubeMusicImporter(
                self.session,
                self.plugin,
                self._file_cache,
            )
        else:
            importer = self.media_importer_from_title_key(parsed.title_key)
        importer.parsed_url = parsed
        return importer

    # TODO: Validate
    @override
    def title_key_from_url(self, url: str) -> str:
        return self._parsed_url(url).title_key

    # TODO: Validate
    def media_importer_from_title_key(self, title_key: str) -> YouTubeImporter:
        # if is_video_key(title_key):
        #     return YouTubeMovieImporter(self.session, self.plugin, self._file_cache)
        # if is_title_key(title_key):
        #     return YouTubeTVShowImporter(self.session, self.plugin, self._file_cache)
        # if is_an_album(title_key):
        #     return YouTubeAlbumImporter(self.session, self.plugin, self._file_cache)
        if is_user_playlist(title_key):
            return YouTubePlaylistImporter(self.session, self.plugin, self._file_cache)
        # if is_topic_channel(self.channel_by_channel_id_file(title_key)):
        #     return YouTubeTopicImporter(self.session, self.plugin, self._file_cache)
        return YouTubeChannelImporter(self.session, self.plugin, self._file_cache)

    # TODO: Validate
    def _channel_by_handle_file(self, channel_handle: str) -> ChannelByHandle:
        return self._cached_file(ChannelByHandle, channel_handle)

    # TODO: Validate
    def _channel_by_username_file(self, channel_username: str) -> ChannelByUsername:
        return self._cached_file(ChannelByUsername, channel_username)

    # TODO: Validate
    def _parsed_url(self, url: str) -> YouTubeParsedURL:
        if match := re.match(self._playlist_video_url_regex(), url):
            parsed = self._parse_playlist(match.group("playlist_key"), url)
            return parsed._replace(video_key=match.group("video_key"))

        # if match := re.match(self._title_playlist_url_regex(), url):
        #     return self._parse_title_playlist(match.group("title_playlist_key"), url)

        if match := re.match(self._playlist_url_regex(), url):
            return self._parse_playlist(match.group("playlist_key"), url)

        if match := re.match(self._video_url_regex(), url):
            return self._parse_video(match.group("video_key"), url)

        if match := re.match(self._channel_key_url_regex(), url):
            return self._parse_channel(match.group("channel_key"), url)

        # if match := re.match(self._title_url_regex(), url):
        #     return self._parse_title(match.group("title_key"), url)

        if match := re.match(self._channel_username_url_regex(), url):
            channel = self._parsed_channel(
                self._channel_by_username_file(match.group("channel_username")),
                url,
            )
            return self._parse_channel(get_first_item(channel.items).id, url)

        if match := re.match(self._channel_handle_url_regex(), url):
            channel = self._parsed_channel(
                self._channel_by_handle_file(match.group("channel_handle")),
                url,
            )
            return self._parse_channel(get_first_item(channel.items).id, url)

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _parsed_channel(self, channel_file: BaseFile[Any], url: str) -> ChannelsModel:
        self.raise_invalid_url_if_no_content(channel_file, url)
        channel: ChannelsModel = channel_file.parsed()
        if not channel.items:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return channel

    # TODO: Validate
    def _raise_if_invalid_channel(self, channel_key: str, url: str) -> None:
        self._parsed_channel(self.channel_by_channel_id_file(channel_key), url)

    # TODO: Validate
    def _parse_playlist(self, playlist_key: str, url: str) -> YouTubeParsedURL:
        if is_channel_uploads_playlist_key(playlist_key):
            title_key = channel_key_from_uploads_playlist_key(playlist_key)
            self._raise_if_invalid_channel(title_key, url)
            # if is_movies_channel(self.channel_by_channel_id_file(title_key)):
            #     return self._movies_channel_parsed_url(title_key, url)
            return YouTubeParsedURL(title_key, playlist_key)

        if is_an_album(playlist_key):
            music_playlist_file = self.music_playlist_file(playlist_key)
            self.raise_invalid_url_if_no_content(music_playlist_file, url)
            artists = music_playlist_file.artists()
            if not artists:
                msg = f"{playlist_key} names no musician it was released by: {url}"
                raise InvalidURLError(msg)
            return YouTubeParsedURL(
                artists[0],
                playlist_key,
                album_playlist_key=playlist_key,
            )

        playlist_items_file = self.playlist_items_file(playlist_key)
        self.raise_invalid_url_if_no_content(playlist_items_file, url)
        title_key = get_first_item(playlist_items_file.items()).snippet.channel_id
        return YouTubeParsedURL(title_key, playlist_key)

    # TODO: Validate
    def _parse_video(self, video_key: str, url: str) -> YouTubeParsedURL:
        videos_file = self.videos_file(video_key)
        self.raise_invalid_url_if_no_content(videos_file, url)

        channel_key = videos_file.parsed().items[0].snippet.channel_id
        # if is_free_movies_channel(channel_key):
        #     return YouTubeParsedURL(video_key, video_key, video_key=video_key)

        self._raise_if_invalid_channel(channel_key, url)

        # if is_movies_channel(self.channel_by_channel_id_file(channel_key)):
        #     return self._movies_channel_parsed_url(channel_key, url)

        # if is_topic_channel(self.channel_by_channel_id_file(channel_key)):
        #     return YouTubeParsedURL(
        #         channel_key,
        #         channel_key,
        #         video_key=video_key,
        #         musician_track=True,
        #     )
        return YouTubeParsedURL(
            channel_key,
            channel_uploads_playlist_key(channel_key),
            video_key=video_key,
        )

    #     # TODO: Validate
    #     def _parse_title_playlist(
    #         self,
    #         title_playlist_key: str,
    #         url: str,
    #     ) -> YouTubeParsedURL:
    #         title_listing_file = self.browse_file(title_playlist_key)
    #         self.raise_invalid_url_if_no_content(title_listing_file, url)
    #         title_key = title_listing_file.title_key()
    #         if title_key is None:
    #             msg = f"Invalid {self.plugin_name()} URL: {url}"
    #             raise InvalidURLError(msg)
    #         return YouTubeParsedURL(title_key, title_key, whole_title=True)

    # #     # TODO: Validate
    #     def _parse_title(self, title_key: str, url: str) -> YouTubeParsedURL:
    #         self.raise_invalid_url_if_no_content(self.browse_file(title_key), url)
    #         if not title_season_numbers_from_file(self.browse_file(title_key)):
    #             msg = f"Invalid {self.plugin_name()} URL: {url}"
    #             raise InvalidURLError(msg)

    #         season = parse_qs(urlparse(url).query).get("season", [])
    #         if season:
    #             return YouTubeParsedURL(
    #                 title_key,
    #                 title_season_key(title_key, season[0]),
    #             )
    #         return YouTubeParsedURL(title_key, title_key, whole_title=True)

    #     # TODO: Validate
    def _parse_channel(self, title_key: str, url: str) -> YouTubeParsedURL:
        self._raise_if_invalid_channel(title_key, url)

        # if is_free_movies_channel(title_key):
        #     msg = (
        #         f"{title_key} does not list most of the videos it owns, so import "
        #         f"the URL of an individual video instead of the channel: {url}"
        #     )
        #     raise InvalidURLError(msg)

        # if is_movies_channel(self.channel_by_channel_id_file(title_key)):
        #     return self._movies_channel_parsed_url(title_key, url)

        # if is_topic_channel(self.channel_by_channel_id_file(title_key)):
        #     return YouTubeParsedURL(title_key, title_key, whole_title=True)
        return YouTubeParsedURL(title_key, channel_uploads_playlist_key(title_key))


#     # TODO: Validate
#     def _movies_channel_parsed_url(
#         self,
#         channel_key: str,
#         url: str,
#     ) -> YouTubeParsedURL:
#         video_key = self._movies_channel_video_key(channel_key)
#         if video_key is None:
#             msg = (
#                 f"{channel_key} uploaded no video that could be read as the film "
#                 f"it was generated for: {url}"
#             )
#             raise InvalidURLError(msg)
#         return YouTubeParsedURL(video_key, video_key, video_key=video_key)

# #     # TODO: Validate
#     def _movies_channel_video_key(self, channel_key: str) -> str | None:
#         uploads_file = self.playlist_items_file(
#             channel_uploads_playlist_key(channel_key),
#         )
#         if not uploads_file.record_content:
#             return None
#         video_keys = [
#             item.content_details.video_id
#             for item in uploads_file.items()
#             if video_is_valid(item.snippet.title)
#         ]
#         if not video_keys:
#             return None
#         batch_download_missing_videos(
#             [self.videos_file(video_key) for video_key in video_keys],
#         )
#         for video_key in video_keys:
#             if is_usa_video(self.videos_file(video_key)):
#                 return video_key
#         return video_keys[0]
