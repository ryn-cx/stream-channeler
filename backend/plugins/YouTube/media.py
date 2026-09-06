# TODO: Validate
"""Reading a YouTube address and writing what it names into the database."""

from __future__ import annotations

import re
from contextlib import suppress
from datetime import timedelta
from typing import TYPE_CHECKING, Any, override
from urllib.parse import parse_qs, urlparse

from loguru import logger
from not_yt_dlapi.exceptions import (
    ChannelFeedNotFoundError,
    PlaylistFeedNotFoundError,
)
from sqlmodel import col

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.utils.base_plugin.url import MediaInfo
from plugins.YouTube.constants import LONG_DOMAIN_REGEX, SHORT_DOMAIN_REGEX
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.utils import (
    best_thumbnail_url,
    channel_key_from_uploads_playlist_key,
    channel_uploads_playlist_key,
    channel_url,
    get_first_item,
    is_an_album,
    is_channel_uploads_playlist_key,
    is_free_movies_channel,
    is_show_key,
    is_show_season_key,
    is_user_playlist,
    is_video_key,
    playlist_url,
    show_season_key,
    show_season_url,
    show_url,
    split_show_season_key,
    thumbnail_url,
    video_is_valid,
    video_url,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from not_yt_dlapi.channels.models import ChannelsModel
    from not_yt_dlapi.channels.models import Item as ChannelItem
    from not_yt_dlapi.playlists.models import Item as PlaylistsItem

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile
    from plugins.YouTube.files import MusicPlaylist, PlaylistFeed

PENDING_UPDATE_STATUS = "Pending update"

# https://www.youtube.com/watch?v=lVI_J1cbFb4&list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
# https://youtu.be/lVI_J1cbFb4?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
PLAYLIST_VIDEO_URL_REGEX = (
    rf"(?:{LONG_DOMAIN_REGEX}|{SHORT_DOMAIN_REGEX})"
    r"\/(?:watch\?v=)?(?P<video_key>[A-Za-z0-9_-]{11})[?&]"
    r"list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
)
# https://www.youtube.com/playlist?list=TVSHX2-tv9KBHSAWLsDbH3h9vNzwxEAyyqXMw
SHOW_PLAYLIST_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/playlist\?list=(?P<show_playlist_key>TVSH[^&]+)"
)
# https://www.youtube.com/playlist?list=PLuhl9TnQPDCnWIhy_KSbtFwXVQnNvgfSh
PLAYLIST_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/playlist\?list=(?P<playlist_key>(?:PL|OLAK5uy_|UU)[^&]+)"
)
# https://www.youtube.com/watch?v=jNQXAC9IVRw
# https://www.youtube.com/shorts/jNQXAC9IVRw
# https://youtu.be/jNQXAC9IVRw
VIDEO_URL_REGEX = (
    rf"(?:{LONG_DOMAIN_REGEX}\/(?:watch\?v=|shorts\/)|{SHORT_DOMAIN_REGEX}\/)"
    r"(?P<video_key>[A-Za-z0-9_-]{11})(?:$|[?&])"
)
# https://www.youtube.com/channel/UC4QobU6STFB0P71PMvOGN5A
CHANNEL_KEY_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/channel\/(?P<channel_key>UC.{22})(?:$|\/)"
)
# https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw
# https://www.youtube.com/show/SCYT6SmwXZxUksg_rJd_nzuw?season=23&sbp=...
SHOW_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/show\/(?P<show_key>SC[A-Za-z0-9_-]+?)(?:$|[/?])"
)
# https://www.youtube.com/user/jawed
CHANNEL_USERNAME_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/user\/(?P<channel_username>.+?)(?:$|\/)"
)
# https://www.youtube.com/@jawed
# https://www.youtube.com/c/jawed
# https://www.youtube.com/jawed
CHANNEL_HANDLE_URL_REGEX = (
    LONG_DOMAIN_REGEX + r"\/(?:c\/|@)?(?P<channel_handle>.+?)(?:$|\/)"
)


# TODO: Validate
class YouTubeMedia(YouTubeShared, BaseImporter):
    _show_key: str
    _playlist_key: str
    _video_key: str | None
    _whole_show: bool
    _musician_track: bool

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return (
            PLAYLIST_VIDEO_URL_REGEX,  # Must be first due to regex overlap
            SHOW_PLAYLIST_URL_REGEX,
            PLAYLIST_URL_REGEX,
            VIDEO_URL_REGEX,
            CHANNEL_KEY_URL_REGEX,
            SHOW_URL_REGEX,
            CHANNEL_USERNAME_URL_REGEX,
            CHANNEL_HANDLE_URL_REGEX,
        )

    # Every address carries the domain it is written under, because a video is
    # named on the long domain and the short one alike, so the domain is not put
    # in front of them here the way it is for every other plugin.
    # TODO: Validate
    @classmethod
    @override
    def url_regex(cls) -> str:
        alternatives = "|".join(
            # Strip named groups to non-capturing so addresses that share a group name
            # (e.g. playlist_key) do not collide when the alternatives are combined.
            re.sub(r"\(\?P<[^>]+>", "(?:", url_regex)
            for url_regex in cls._url_regexes()
        )
        return f"(?:{alternatives})"

    # TODO: Validate
    @override
    def extract_media_info(self, url: str) -> MediaInfo:
        self._read_url(url)
        if self._whole_show:
            return MediaInfo(self._show_key)
        if self._video_key is None:
            return MediaInfo(self._show_key, season_key=self._playlist_key)
        # The track is looked for in every release of the musician, since the URL
        # named no release and the show holds one season for each of them.
        if self._musician_track:
            return MediaInfo(self._show_key, episode_key=self._video_key)
        return MediaInfo(
            self._show_key,
            season_key=self._playlist_key,
            episode_key=self._video_key,
        )

    # TODO: Validate
    def _read_url(self, url: str) -> None:  # noqa: PLR0911 - One return per kind of address.
        self._video_key = None
        self._whole_show = False
        self._musician_track = False

        if match := re.match(PLAYLIST_VIDEO_URL_REGEX, url):
            self._video_key = match.group("video_key")
            self._read_playlist(match.group("playlist_key"), url)
            return

        if match := re.match(SHOW_PLAYLIST_URL_REGEX, url):
            self._read_show_playlist(match.group("show_playlist_key"), url)
            return

        if match := re.match(PLAYLIST_URL_REGEX, url):
            self._read_playlist(match.group("playlist_key"), url)
            return

        if match := re.match(VIDEO_URL_REGEX, url):
            self._read_video(match.group("video_key"), url)
            return

        if match := re.match(CHANNEL_KEY_URL_REGEX, url):
            channel_key = match.group("channel_key")
            self._parsed_channel(self.channel_by_channel_id_file(channel_key), url)
            self._read_channel(channel_key, url)
            return

        if match := re.match(SHOW_URL_REGEX, url):
            self._read_show(match.group("show_key"), url)
            return

        if match := re.match(CHANNEL_USERNAME_URL_REGEX, url):
            parsed = self._parsed_channel(
                self.channel_by_username_file(match.group("channel_username")),
                url,
            )
            self._read_channel(get_first_item(parsed.items).id, url)
            return

        if match := re.match(CHANNEL_HANDLE_URL_REGEX, url):
            parsed = self._parsed_channel(
                self.channel_by_handle_file(match.group("channel_handle")),
                url,
            )
            self._read_channel(get_first_item(parsed.items).id, url)
            return

        msg = f"Invalid {self.plugin_name()} URL: {url}"
        raise InvalidURLError(msg)

    # TODO: Validate
    def _parsed_channel(self, channel_file: BaseFile[Any], url: str) -> ChannelsModel:
        self.raise_if_invalid_file(channel_file, url)
        channel: ChannelsModel = channel_file.parsed()
        # The API answers a channel it has nothing under with an empty listing
        # rather than by refusing, so a URL naming no channel is only known from
        # what came back holding none.
        if not channel.items:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        return channel

    # TODO: Validate
    def _raise_if_invalid_channel(self, channel_key: str, url: str) -> None:
        self._parsed_channel(self.channel_by_channel_id_file(channel_key), url)

    # TODO: Validate
    def _read_playlist(self, playlist_key: str, url: str) -> None:
        self._playlist_key = playlist_key

        # A channel's uploads are a season of that channel rather than a listing of
        # their own, and the playlist they are listed as is named after the channel,
        # so the channel is read off the key rather than looked up.
        if is_channel_uploads_playlist_key(playlist_key):
            self._show_key = channel_key_from_uploads_playlist_key(playlist_key)
            self._raise_if_invalid_channel(self._show_key, url)
            return

        # A release belongs to the musician's Topic channel, which is the show its
        # tracks went up on, so importing it brings in the musician rather than the
        # release on its own. A release whose tracks went up somewhere else is its
        # own show, since a channel that is not a Topic lists far more than music.
        if is_an_album(playlist_key):
            music_playlist_file = self.music_playlist_file(playlist_key)
            self.raise_if_invalid_file(music_playlist_file, url)
            channel_key = music_playlist_file.artist_channel_id()
            if not channel_key:
                self._show_key = playlist_key
                return
            # The release is imported as one of the musician's when the channel its
            # tracks went up on is a Topic channel, which is something only that
            # channel says.
            self._raise_if_invalid_channel(channel_key, url)
            # Nothing the channel lists names the release, so what the URL named is
            # remembered for the seasons of the channel to be read with.
            self.record_album_playlist_key(playlist_key)
            self._show_key = channel_key
            return

        playlist_items_file = self.playlist_items_file(playlist_key)
        self.raise_if_invalid_file(playlist_items_file, url)
        self._show_key = get_first_item(
            playlist_items_file.parsed().items,
        ).snippet.channel_id

    # TODO: Validate
    def _read_video(self, video_key: str, url: str) -> None:
        self._video_key = video_key
        videos_file = self.videos_file(video_key)
        self.raise_if_invalid_file(videos_file, url)

        channel_key = videos_file.parsed().items[0].snippet.channel_id
        # A channel that never lists this video cannot be imported to reach it, so the
        # video is imported as a show of its own instead.
        if is_free_movies_channel(channel_key):
            self._show_key = video_key
        else:
            self._show_key = channel_key

        if is_video_key(self._show_key):
            self._playlist_key = self._show_key
            return

        # Whether the show the video belongs to is a musician rather than a channel
        # is something only the channel says, and what the URL brought in is named
        # by seasons that differ between the two.
        self._raise_if_invalid_channel(self._show_key, url)

        # A track on a Topic channel is listed by the release it is on rather than
        # by an uploads season, and which release that is only the musician's own
        # listing says, so the URL asks for the musician.
        if self.is_topic_channel(self._show_key):
            self._playlist_key = self._show_key
            self._musician_track = True
        else:
            self._playlist_key = channel_uploads_playlist_key(self._show_key)

    # TODO: Validate
    def _read_show_playlist(self, show_playlist_key: str, url: str) -> None:
        show_listing_file = self.show_listing_file(show_playlist_key)
        self.raise_if_invalid_file(show_listing_file, url)
        show_key = show_listing_file.show_key()
        if show_key is None:
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)
        self._show_key = show_key
        self._playlist_key = show_key
        self._whole_show = True
        self.raise_if_invalid_file(self.show_page_file(show_key), url)

    # TODO: Validate
    def _read_show(self, show_key: str, url: str) -> None:
        self._show_key = show_key
        # The page names the playlist the listing is asked for by, so it is read
        # before the listing rather than beside it.
        self.raise_if_invalid_file(self.show_page_file(show_key), url)
        self.raise_if_invalid_file(self.show_listing_file_for_show(show_key), url)
        if not self.show_season_numbers_from_file(show_key):
            msg = f"Invalid {self.plugin_name()} URL: {url}"
            raise InvalidURLError(msg)

        # A URL for one season only asks for that season, where a URL for the show
        # asks for all of it.
        season = parse_qs(urlparse(url).query).get("season", [])
        if season:
            self._playlist_key = show_season_key(show_key, season[0])
        else:
            self._playlist_key = show_key
            self._whole_show = True

    # TODO: Validate
    def _read_channel(self, show_key: str, url: str) -> None:
        self._show_key = show_key
        # A handle and a username are looked up in files of their own, and the
        # channel the key names is what says whether it is a Topic channel, so it is
        # read here rather than left to whatever asks first.
        self._raise_if_invalid_channel(show_key, url)

        # The channel only lists a fraction of the videos it owns, so importing it
        # would import almost none of them. Its videos are imported one at a time.
        if is_free_movies_channel(show_key):
            msg = (
                f"{show_key} does not list most of the videos it owns, so import "
                f"the URL of an individual video instead of the channel: {url}"
            )
            raise InvalidURLError(msg)

        # A Topic channel has no uploads season, because what it lists is releases,
        # so the URL asks for the channel itself the way a show URL does.
        if self.is_topic_channel(show_key):
            self._playlist_key = show_key
            self._whole_show = True
        else:
            self._playlist_key = channel_uploads_playlist_key(show_key)

    # A YouTube show is always imported for a specific playlist.
    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        media_info = self.extract_media_info(url)
        show_key = media_info.show_key
        existing_show = self._preload_show(
            show_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_show:
            existing_show = self.upsert_show(self.source, show_key)

        # If a channel is imported but a new playlist is added and that playlist is the
        # URL being imported this will update the channel information to include that
        # playlist.
        elif self._playlist_is_missing(existing_show, self._playlist_key):
            self._download_if_outdated(
                self._show_files(show_key),
                tz_datetime.now(),
            )
            existing_show = self.upsert_show(self.source, show_key)

        return self._import_results(existing_show, media_info)

    # TODO: Validate
    def update_seasons(self, seasons: Sequence[Season]) -> None:
        """Update multiple seasons at once to reduce the number of API calls."""
        for season in seasons:
            self.check_feed_for_new_files(season)
            self.session.commit()

        self._update_marked_seasons()

    # TODO: Validate
    def _update_marked_seasons(self) -> None:
        seasons = self._season_with_new_episodes_available()

        video_keys: list[str] = []
        for season in seasons:
            video_keys.extend(
                key
                for key in self._episode_keys_from_season_files(
                    season.key,
                    season.show.key,
                )
                if key not in video_keys
            )

        self._batch_download_missing_videos(video_keys)

        for season in seasons:
            self._update_and_upsert_show(season.show)
            season.status = None
            self.session.commit()
            self.clear_file_cache()

    # TODO: Validate
    def _season_with_new_episodes_available(self) -> list[Season]:
        statement = Season.select_with_plugin_eager().where(
            col(Plugin.key) == self.plugin_name(),
            col(Season.deleted_at).is_(None),
            col(Season.status) == PENDING_UPDATE_STATUS,
        )
        return list(self.session.exec(statement).unique().all())

    # TODO: Validate
    def check_feed_for_new_files(self, season: Season) -> None:
        playlist_feed = self.playlist_feed_file(season.key)

        # If the file does not exist just download the initial file. The first update
        # will be delayed a bit but it's acceptable for code that is easier to work
        # with.
        if playlist_feed.does_not_exist():
            with suppress(ChannelFeedNotFoundError, PlaylistFeedNotFoundError):
                self._download_season_feed(season)
            return

        old_feed_video_ids = set(playlist_feed.video_ids())
        try:
            self._download_season_feed(season)
        except ChannelFeedNotFoundError, PlaylistFeedNotFoundError:
            return

        new_video_ids = set(playlist_feed.video_ids()) - old_feed_video_ids
        if not new_video_ids:
            return

        logger.info(
            "Found {} new videos in season {}: {}",
            len(new_video_ids),
            season.name or season.key,
            ", ".join(sorted(new_video_ids)),
        )
        season.status = PENDING_UPDATE_STATUS
        self.playlist_items_file(season.key).download_if_outdated(tz_datetime.now())

    # TODO: Validate
    def _download_season_feed(self, season: Season) -> PlaylistFeed:
        playlist_feed = self.playlist_feed_file(season.key)
        try:
            playlist_feed.download_if_outdated(season.update_at)
        except ChannelFeedNotFoundError, PlaylistFeedNotFoundError:
            season.update_at = tz_datetime.now() + timedelta(hours=1)
            raise

        season.update_at = playlist_feed.data_timestamp() + timedelta(hours=6)
        return playlist_feed

    # TODO: Validate
    @override
    def tmdb_lookup_info(self, show_key: str) -> list[TMDBLookupInfo]:
        """Return what to look a title up on TMDB by, where TMDB holds one.

        A channel, a playlist and a musician's releases are things YouTube has
        and TMDB does not, so nothing is looked up for them and they are left
        standing for themselves.
        """
        show = self._preload_show(show_key).one_or_none()
        if show is None or not show.name:
            return []
        return [TMDBLookupInfo(show.name, self.tmdb_media_type(show_key), None)]

    # TODO: Validate
    @override
    def upsert_show(  # noqa: PLR0911 - One return per kind of title.
        self,
        source: Source,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        if is_video_key(show_key):
            return self._upsert_show_movie(show_key, force=force)
        if is_show_key(show_key):
            return self._upsert_show_series(show_key, force=force)
        if is_an_album(show_key):
            return self._upsert_show_music(show_key, force=force)
        if is_user_playlist(show_key):
            return self._upsert_show_playlist(show_key, force=force)
        if self.is_topic_channel(show_key):
            return self._upsert_show_topic(show_key, force=force)
        if self.is_movies_channel(show_key):
            return self._upsert_show_channel(
                self.paid_or_free_source(show_key),
                show_key,
                force=force,
            )
        return self._upsert_show_channel(source, show_key, force=force)

    # TODO: Validate
    def _upsert_show_series(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        show_page = self.show_page_file(show_key)
        source = self.paid_or_free_source(show_key)

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=show_page.title(),
                url=show_url(show_key),
                media_type="Series",
                data_timestamp=data_timestamp,
                # A show only changes when a season is added to it.
                update_at=data_timestamp + timedelta(days=7),
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_seasons_series(show, show_key, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_seasons_series(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for season_key in self._season_keys_from_show_files(show_key):
            _, season_number = split_show_season_key(season_key)
            season = Season.get_from_memory(self.session, show, season_key)
            if self._season_is_outdated(season, show_key, force=force):
                data_timestamps = self.season_data_timestamps(season_key, show_key)
                data_timestamp = data_timestamps[0]
                new_season = Season(
                    key=season_key,
                    name=f"Season {season_number}",
                    season_number=int(season_number),
                    url=show_season_url(show_key, season_number),
                    data_timestamp=data_timestamp,
                    # A show only changes when a season or an episode is added
                    # to it.
                    update_at=data_timestamp + timedelta(days=7),
                    show_id=show.id,
                )
                season = new_season.upsert(show, season)
                season.set_update_at(None, data_timestamps)
            self._upsert_episodes(season, show_key, force=force)

    # TODO: Validate
    def _upsert_show_channel(
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
            data_timestamps = self.show_data_timestamps(show_key)
            new_show = Show(
                key=channel_item.id,
                name=self._channel_show_name(show_key, channel_item),
                url=channel_url(channel_item.id),
                media_type="Movie"
                if self.is_movies_channel(show_key)
                else "YouTube Channel",
                # Updating every 30 days is reasonable because this is only used for
                # checking for new playlists and changes to the channel information.
                update_at=channel_file.data_timestamp() + timedelta(days=365),
                data_timestamp=data_timestamps[0],
                canonical_show_validated_at=None
                if self.is_movies_channel(show_key)
                else tz_datetime.now(),
                source_id=source.id,
                image_url=best_thumbnail_url(channel_item.snippet.thumbnails),
                thumbnail_url=thumbnail_url(channel_item.snippet.thumbnails),
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_seasons_channel(show, show_key, force=force)
        self._soft_delete_missing(show_key)
        if self.is_movies_channel(show_key):
            self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _channel_show_name(
        self,
        show_key: str,
        channel_item: ChannelItem,
    ) -> str | None:
        # Every channel generated for a title of YouTube's catalogue is named after
        # the catalogue rather than after the title, so the title is read off what
        # the channel uploaded, which is that one title however many times over.
        if not self.is_movies_channel(show_key):
            return channel_item.snippet.title
        episode_keys = self.show_episode_keys_from_files(show_key)
        if not episode_keys:
            return channel_item.snippet.title
        items = self.videos_file(episode_keys[0]).parsed().items
        return items[0].snippet.title if items else channel_item.snippet.title

    # TODO: Validate
    def _upsert_show_movie(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        video_item = get_first_item(self.videos_file(show_key).parsed().items)
        source = self.paid_or_free_source(show_key)

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=video_item.snippet.title,
                # A YouTube video with a null character in the description caused
                # importing to hang so it needs to be stripped out.
                description=video_item.snippet.description.replace("\x00", ""),
                url=video_url(show_key),
                media_type="Movie",
                image_url=best_thumbnail_url(video_item.snippet.thumbnails),
                thumbnail_url=thumbnail_url(video_item.snippet.thumbnails),
                data_timestamp=data_timestamp,
                # Movies are only updated once a year to make sure they are still
                # available.
                update_at=data_timestamp + timedelta(days=365),
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        self._upsert_season_movie(show, show_key, force=force)
        self._soft_delete_missing(show_key)
        self.link_show_to_tmdb(show)

        return show

    # TODO: Validate
    def _upsert_season_movie(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, show, show_key)
        if self._season_is_outdated(season, show_key, force=force):
            video_item = get_first_item(self.videos_file(show_key).parsed().items)
            data_timestamps = self.season_data_timestamps(show_key, show_key)
            data_timestamp = data_timestamps[0]
            new_season = Season(
                key=show_key,
                name=video_item.snippet.title,
                image_url=best_thumbnail_url(video_item.snippet.thumbnails),
                thumbnail_url=thumbnail_url(video_item.snippet.thumbnails),
                data_timestamp=data_timestamp,
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(data_timestamp, data_timestamps)
        self._upsert_episodes(season, show_key, force=force)

    # TODO: Validate
    def _upsert_show_playlist(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        playlist_item = get_first_item(
            self.playlist_info_file(show_key).parsed().items,
        )
        source = self.links_source

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=playlist_item.snippet.title,
                description=playlist_item.snippet.description.replace("\x00", ""),
                url=playlist_url(show_key),
                media_type="Series",
                image_url=best_thumbnail_url(playlist_item.snippet.thumbnails),
                thumbnail_url=thumbnail_url(playlist_item.snippet.thumbnails),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(hours=6), data_timestamps)

        self._upsert_season(
            show=show,
            show_key=show_key,
            season_key=show_key,
            name=playlist_item.snippet.title,
            playlist=playlist_item,
            force=force,
        )
        self._soft_delete_missing(show_key)

        return show

    # TODO: Validate
    def _upsert_show_music(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        music_playlist = self.music_playlist_file(show_key)
        source = self.source

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=self._music_name(music_playlist),
                url=playlist_url(show_key),
                media_type=f"YouTube {music_playlist.release_type() or 'Album'}",
                image_url=music_playlist.image_url(),
                thumbnail_url=music_playlist.image_url(),
                data_timestamp=data_timestamp,
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(data_timestamp + timedelta(days=365), data_timestamps)

        self._upsert_season_music(
            show,
            show_key,
            show_key,
            self._music_name(music_playlist),
            force=force,
        )
        self._soft_delete_missing(show_key)

        return show

    # TODO: Validate
    def _upsert_show_topic(
        self,
        show_key: str,
        *,
        force: bool = False,
    ) -> Show:
        """Upsert the musician a Topic channel is generated for.

        A release of theirs is a season of this show rather than a show of its
        own, which is what makes importing the channel import all of their music
        the way importing a channel imports all of its playlists.
        """
        source = self.source

        show = Show.get_from_memory(self.session, source, show_key)
        if self._show_is_outdated(show, force=force):
            channel_item = get_first_item(
                self.channel_by_channel_id_file(show_key).parsed().items,
            )
            data_timestamps = self.show_data_timestamps(show_key)
            data_timestamp = data_timestamps[0]
            new_show = Show(
                key=show_key,
                name=channel_item.snippet.title,
                url=channel_url(show_key),
                media_type="YouTube Artist",
                image_url=best_thumbnail_url(channel_item.snippet.thumbnails),
                thumbnail_url=thumbnail_url(channel_item.snippet.thumbnails),
                data_timestamp=data_timestamp,
                # A musician only changes when they put something out.
                update_at=data_timestamp + timedelta(days=365),
                source_id=source.id,
            )
            show = new_show.upsert(source, show)
            show.set_update_at(None, data_timestamps)

        for season_key in self._season_keys_from_show_files(show_key):
            music_playlist = self.music_playlist_file(season_key)
            self._upsert_season_music(
                show,
                season_key,
                show_key,
                music_playlist.title(),
                force=force,
            )
        self._soft_delete_missing(show_key)

        return show

    # TODO: Validate
    def _upsert_season_music(
        self,
        show: Show,
        season_key: str,
        show_key: str,
        name: str | None,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, show, season_key)
        if self._season_is_outdated(season, show_key, force=force):
            music_playlist = self.music_playlist_file(season_key)
            data_timestamps = self.season_data_timestamps(season_key, show_key)
            data_timestamp = data_timestamps[0]
            new_season = Season(
                key=season_key,
                name=name,
                url=playlist_url(season_key),
                image_url=music_playlist.image_url(),
                thumbnail_url=music_playlist.image_url(),
                data_timestamp=data_timestamp,
                show_id=show.id,
            )
            season = new_season.upsert(show, season)
            season.set_update_at(data_timestamp + timedelta(days=365), data_timestamps)
        self._upsert_episodes(season, show_key, force=force)

    # TODO: Validate
    @staticmethod
    def _music_name(music_playlist: MusicPlaylist) -> str | None:
        title = music_playlist.title()
        artists = music_playlist.artists()
        if not title or not artists:
            return title
        return f"{title} - {', '.join(artists)}"

    # TODO: Validate
    def _upsert_seasons_channel(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        self._upsert_season_channel_uploads(show, show_key, force=force)
        if self.is_movies_channel(show_key):
            return
        self._upsert_seasons_playlist(show, show_key, force=force)
        self._upsert_seasons_album(show, show_key, force=force)

    # TODO: Validate
    def _upsert_seasons_album(
        self,
        show: Show,
        show_key: str,
        *,
        force: bool = False,
    ) -> None:
        for season_key in self._album_season_keys_from_database(show_key):
            music_playlist = self.music_playlist_file(season_key)
            self._upsert_season_music(
                show,
                season_key,
                show_key,
                music_playlist.title(),
                force=force,
            )

    # TODO: Validate
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
            data_timestamps = self.season_data_timestamps(season_key, show_key)
            season = Season(
                key=season_key,
                name=name,
                url=playlist_url(season_key),
                image_url=best_thumbnail_url(playlist.snippet.thumbnails),
                thumbnail_url=thumbnail_url(playlist.snippet.thumbnails),
                data_timestamp=data_timestamps[0],
                show_id=show.id,
            ).upsert(show, season)
            season.set_update_at(
                data_timestamps[0] + timedelta(hours=6),
                data_timestamps,
            )
        self._upsert_episodes(season, show_key, force=force)

    # TODO: Validate
    def _upsert_season_channel_uploads(
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
        uploads_key = channel_uploads_playlist_key(show.key)
        self._upsert_season(
            show=show,
            show_key=show_key,
            season_key=uploads_key,
            name=f"Uploads from {show.name}",
            playlist=channel_item,
            force=force,
        )

    # TODO: Validate
    def _upsert_seasons_playlist(
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
        uploads_key = channel_uploads_playlist_key(show.key)
        for season_key in self._season_keys_from_show_files(show_key):
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

    # TODO: Validate
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
        if is_show_season_key(season.key) or is_an_album(season.key):
            episode_keys = self._season_episode_keys_from_file(season.key)
            for position, episode_key in enumerate(episode_keys):
                self._upsert_episode(
                    season,
                    show_key,
                    episode_key,
                    position,
                    force=force,
                )
            return

        usa_only = self.is_movies_channel(show_key)
        seen: set[str] = set()
        for item in self.playlist_items_file(season.key).parsed().items:
            episode_key = item.content_details.video_id
            if not video_is_valid(item.snippet.title) or episode_key in seen:
                continue
            if usa_only and not self.is_usa_video(episode_key):
                continue
            seen.add(episode_key)
            self._upsert_episode(
                season,
                show_key,
                episode_key,
                item.snippet.position,
                force=force,
            )

    # TODO: Validate
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

        video_duration = video_item.content_details.duration
        duration = None
        if video_duration:
            duration = int(video_duration.total_seconds())

        data_timestamps = self.episode_data_timestamps(
            episode_key,
            season.key,
            show_key,
        )
        new_episode = Episode(
            key=video_item.id,
            watch_identifier=watch_identifier(self.plugin_name(), video_item.id),
            name=video_snippet.title,
            url=video_url(video_item.id),
            # A YouTube video with a null character in the description caused
            # importing to hang so it needs to be stripped out.
            description=video_snippet.description.replace("\x00", ""),
            air_date=video_snippet.published_at,
            duration=duration,
            image_url=best_thumbnail_url(video_snippet.thumbnails),
            thumbnail_url=thumbnail_url(video_snippet.thumbnails),
            sort_order=sort_order,
            episode_number=self._get_episode_number(episode_key, season.key, show_key),
            data_timestamp=data_timestamps[0],
            season_id=season.id,
        )

        episode = new_episode.upsert(season, episode)
        episode.set_update_at(None, data_timestamps)
