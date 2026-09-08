# TODO: Validate
"""Reading a YouTube address and writing what it names into the database."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, override

from app.canonical_media.keys import watch_identifier
from app.episodes.models import Episode
from app.media.media_type import TMDBMediaType
from app.seasons.models import Season
from app.titles.models import Title
from app.utils import tz_datetime
from plugins.utils.abstract_plugin import InvalidURLError, TMDBLookupInfo
from plugins.utils.base_plugin.importer import BaseImporter
from plugins.YouTube.constants import (
    URL_REGEXES,
)
from plugins.YouTube.shared import YouTubeShared
from plugins.YouTube.utils import (
    batch_download_missing_videos,
    channel_uploads_playlist_key,
    get_first_item,
    image_url,
    is_channel_key,
    # is_title_key,
    # is_title_season_key,
    is_topic_channel,
    # is_video_key,
    thumbnail_url,
    video_url,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile
    from plugins.utils.base_plugin.url import URLTitleInfo
    from plugins.YouTube.url_parser import ParsedURL


# TODO: Validate
class YouTubeImporter(YouTubeShared, BaseImporter, ABC):
    parsed_url: ParsedURL | None = None

    # TODO: Validate
    @abstractmethod
    def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
        """Return the episode keys held by a single season."""

    # TODO: Validate
    @abstractmethod
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None: ...

    # TODO: Validate
    @override
    def soft_delete_missing_seasons(self, title_key: str) -> None:
        return

    # TODO: Validate
    def tmdb_media_type(
        self,
        title_key: str,  # noqa: ARG002 - Matches how every other file is asked for.
    ) -> TMDBMediaType:
        # return TMDBMediaType.movie if is_video_key(title_key) else TMDBMediaType.tv
        return TMDBMediaType.tv

    # TODO: Validate
    def _get_episode_number(
        self,
        episode_key: str,  # noqa: ARG002 - Matches how every other file is asked for.
        season_key: str,  # noqa: ARG002 - Matches how every other file is asked for.
        title_key: str,  # noqa: ARG002 - Matches how every other file is asked for.
    ) -> int | None:
        return None

    # TODO: Validate
    def _episode_number_from_file_order(
        self,
        episode_key: str,
        season_key: str,
    ) -> int | None:
        episode_keys = self._season_episode_keys_from_file(season_key)
        if episode_key not in episode_keys:
            return None
        return episode_keys.index(episode_key) + 1

    # TODO: Validate
    def _playlist_is_missing(self, title: Title, playlist_key: str) -> bool:
        # A URL for a whole title asks for every season it has, so nothing is missing
        # as long as it has been imported with seasons.
        # if is_title_key(playlist_key) and not is_title_season_key(playlist_key):
        #     return not title.active_children

        # A URL for a Topic channel asks for every release the musician has, which
        # is the whole title, so nothing is missing once it has been imported with
        # seasons.
        if playlist_key == title.key and is_topic_channel(
            self.channel_by_channel_id_file(title.key),
        ):
            return not title.active_children

        # If the playlist being checked is the channel uploads playlist it should only
        # be considered missing if the channel has at least one upload.
        if playlist_key == channel_uploads_playlist_key(title.key):
            channel_by_channel_id = self.channel_by_channel_id_file(title.key)
            channel_item = get_first_item(channel_by_channel_id.parsed().items)
            if int(channel_item.statistics.video_count) == 0:
                return False
        return not Season.get_from_memory(self.session, title, playlist_key)

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        # Required to detect changes to the episode.
        return [self.videos_file(episode_key)]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        title_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        seen: set[str] = set()
        video_keys: list[str] = []
        for season_key in season_keys:
            for video_key in self._season_episode_keys_from_file(season_key):
                if video_key in seen:
                    continue
                seen.add(video_key)
                video_keys.append(video_key)
        return video_keys

    # TODO: Validate
    @override
    def _download_initial_files(self, title_key: str) -> None:
        if is_channel_key(title_key):
            self.channel_by_channel_id_file(title_key).download_if_outdated()

        self._download_if_outdated(self._title_files(title_key))
        season_keys = self._season_keys_from_title_files(title_key)
        for season_key in season_keys:
            self._download_if_outdated(self._season_files(season_key, title_key))
        batch_download_missing_videos(
            [
                self.videos_file(video_key)
                for video_key in self._episode_keys_from_season_files(
                    season_keys,
                    title_key,
                )
            ],
        )

    # TODO: Validate
    @override
    def _download_outdated_files(self, title: Title) -> None:
        """Read the channel before the files that depend on what it is.

        Which files describe a channel is not the same for a Topic channel as for
        any other, and only the channel says which it is, so it is read before
        anything asks. Every video of every season is asked for in one batch
        rather than one at a time, since the API answers for fifty at once.
        """
        season_update_at = {season.key: season.update_at for season in title.seasons}
        if is_channel_key(title.key):
            self.channel_by_channel_id_file(title.key).download_if_outdated(
                title.update_at,
            )

        self._download_if_outdated(self._title_files(title.key), title.update_at)
        season_keys = self._season_keys_from_title_files(title.key)
        for season_key in season_keys:
            self._download_if_outdated(
                self._season_files(season_key, title.key),
                season_update_at.get(season_key),
            )
        batch_download_missing_videos(
            [
                self.videos_file(video_key)
                for video_key in self._episode_keys_from_season_files(
                    season_keys,
                    title.key,
                )
            ],
        )

    # TODO: Validate
    @classmethod
    @override
    def _url_regexes(cls) -> tuple[str, ...]:
        return URL_REGEXES

    # TODO: Validate
    @override
    def get_media_info(self, url: str) -> URLTitleInfo:
        return self._parsed_url(url).media_info()

    # TODO: Validate
    def _parsed_url(self, url: str) -> ParsedURL:
        if self.parsed_url is None:
            msg = f"Ask {self.plugin_name()} for the importer of {url} first."
            raise InvalidURLError(msg)
        return self.parsed_url

    # A YouTube title is always imported for a specific playlist.
    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed = self._parsed_url(url)
        media_info = parsed.media_info()
        title_key = media_info.title_key
        existing_title = self._preload_title(
            title_key,
            preload_episodes=True,
        ).one_or_none()

        if not existing_title:
            existing_title = self._upsert_title(self.source, title_key)

        # If a channel is imported but a new playlist is added and that playlist is the
        # URL being imported this will update the channel information to include that
        # playlist.
        elif self._playlist_is_missing(existing_title, parsed.playlist_key):
            self._download_if_outdated(
                self._title_files(title_key),
                tz_datetime.now(),
            )
            existing_title = self._upsert_title(self.source, title_key)

        return self._import_results(existing_title, media_info)

    # TODO: Validate
    def tmdb_lookup_info(self, title: Title) -> list[TMDBLookupInfo]:
        """Return what to look a title up on TMDB by, where TMDB holds one.

        A channel, a playlist and a musician's releases are things YouTube has
        and TMDB does not, so nothing is looked up for them and they are left
        standing for themselves.
        """
        if not title.name:
            return []
        return [TMDBLookupInfo(title.name, self.tmdb_media_type(title.key), None)]

    # TODO: Validate
    def _upsert_episodes_in_file_order(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        episode_keys = self._season_episode_keys_from_file(season.key)
        for position, episode_key in enumerate(episode_keys):
            self._upsert_episode(season, title_key, episode_key, position, force=force)

    # TODO: Validate
    def _upsert_episode(
        self,
        season: Season,
        title_key: str,
        episode_key: str,
        sort_order: int | None,
        *,
        force: bool = False,
    ) -> None:
        episode = Episode.get_from_memory(self.session, season, episode_key)
        if not self._episode_is_outdated(episode, season.key, title_key, force=force):
            return

        video_item = self.videos_file(episode_key).parsed().items[0]
        video_snippet = video_item.snippet

        duration = None
        # TODO: Can this actually be None, type hints might be outdated here.
        if video_duration := video_item.content_details.duration:
            duration = int(video_duration.total_seconds())

        data_timestamps = self._episode_files_data_timestamps(
            episode_key,
            season.key,
            title_key,
        )
        episode = Episode(
            key=video_item.id,
            watch_identifier=watch_identifier(self.plugin_name(), video_item.id),
            name=video_snippet.title,
            url=video_url(video_item.id),
            # A YouTube video with a null character in the description once caused
            # importing to hang so it needs to be stripped out.
            description=video_snippet.description.replace("\x00", ""),
            air_date=video_snippet.published_at,
            duration=duration,
            image_url=image_url(video_snippet.thumbnails),
            thumbnail_url=thumbnail_url(video_snippet.thumbnails),
            sort_order=sort_order,
            episode_number=self._get_episode_number(episode_key, season.key, title_key),
            data_timestamp=max(data_timestamps),
            season_id=season.id,
        ).upsert(season, episode)
        episode.set_update_at(None)
