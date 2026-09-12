# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, Any, override

from app.seasons.models import Season
from app.titles.models import Title
from app.utils import tz_datetime
from app.utils.update_at import staggered_monthly_update_at
from plugins.utils.abstract_plugin import InvalidURLError
from plugins.YouTube.constants import MUSIC_SOURCE_KEY
from plugins.YouTube.importer import YouTubeImporter
from plugins.YouTube.utils import (
    batch_download_missing_videos,
    playlist_url,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.sources.models import Source
    from plugins.utils.abstract_plugin import URLImportResult
    from plugins.utils.base_plugin.files import BaseFile


# TODO: Validate
class YouTubeMusicImporter(YouTubeImporter):
    # TODO: Validate
    @property
    def music_source(self) -> Source:
        return self._sources[MUSIC_SOURCE_KEY]

    # TODO: Validate
    def _album_keys(self, title_key: str) -> list[str]:
        album_keys: list[str] = []
        if self.parsed_url and self.parsed_url.album_playlist_key:
            album_keys.append(self.parsed_url.album_playlist_key)

        existing_title = self._preload_title(
            title_key,
            source_key=MUSIC_SOURCE_KEY,
            preload_seasons=True,
        ).one_or_none()
        if existing_title:
            album_keys.extend(
                season.key
                for season in existing_title.seasons
                if season.key not in album_keys
            )
        return album_keys

    # TODO: Validate
    @override
    def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
        return [
            self.music_playlist_file(album_key)
            for album_key in self._album_keys(title_key)
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        title_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.music_playlist_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_title_files(self, title_key: str) -> list[str]:
        return self._album_keys(title_key)

    # TODO: Validate
    @override
    def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
        return self.music_playlist_file(season_key).track_keys()

    # TODO: Validate
    @override
    def _get_episode_number(
        self,
        episode_key: str,
        season_key: str,
        title_key: str,
    ) -> int | None:
        return self._episode_number_from_file_order(episode_key, season_key)

    # TODO: Validate
    @override
    def _upsert_episodes(
        self,
        season: Season,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        self._upsert_episodes_in_file_order(season, title_key, force=force)

    # TODO: Validate
    @override
    def update_season(self, season: Season) -> None:
        preloaded_season = self._preload_season(season.id, preload_title=True).one()
        self._update_and_upsert_title(preloaded_season.title)

    # TODO: Validate
    @override
    def _preload_and_download_files(self, title: Title | str) -> None:
        title_key = title if isinstance(title, str) else title.key
        season_update_ats: dict[str, Any] = (
            {}
            if isinstance(title, str)
            else {season.key: season.update_at for season in title.seasons}
        )
        album_keys = self._album_keys(title_key)
        for album_key in album_keys:
            self._download_if_outdated(
                self._season_files(album_key, title_key),
                season_update_ats.get(album_key),
            )
        batch_download_missing_videos(
            [
                self.videos_file(track_key)
                for track_key in self._episode_keys_from_season_files(
                    album_keys,
                    title_key,
                )
            ],
        )

    # TODO: Validate
    @override
    def import_url(self, url: str) -> list[URLImportResult]:
        parsed = self._parsed_url(url)
        album_key = parsed.playlist_key
        album_file = self.music_playlist_file(album_key)
        album_file.download_if_outdated()

        artists = album_file.artists()
        if not artists:
            msg = f"{album_key} names no musician it was released by: {url}"
            raise InvalidURLError(msg)

        results: list[URLImportResult] = []
        for artist in artists:
            self.parsed_url = parsed._replace(
                title_key=artist,
                album_playlist_key=album_key,
            )
            self._preload_and_download_files(artist)
            title = self._upsert_title(self.music_source, artist)
            results.extend(
                self._import_results(title, self.parsed_url.media_info()),
            )
        self.parsed_url = parsed
        return results

    # TODO: Validate
    @override
    def _upsert_title(
        self,
        source: Source,
        title_key: str,
        *,
        force: bool = False,
    ) -> Title:
        source = self.music_source

        title = Title.get_from_memory(self.session, source, title_key)
        if self._title_is_outdated(title, force=force):
            data_timestamps = self._title_files_data_timestamps(title_key)
            title = Title(
                key=title_key,
                name=title_key,
                url=None,
                media_type="YouTube Artist",
                data_timestamp=max(data_timestamps),
                update_at=tz_datetime.max(),
                tmdb_title_validated_at=tz_datetime.now(),
                source_id=source.id,
            ).upsert(source, title)
            title.set_update_at(None)

        for album_key in self._album_keys(title_key):
            self._upsert_album_season(title, album_key, title_key, force=force)
        self._soft_delete_missing_seasons_and_episodes(title_key)

        return title

    # TODO: Validate
    def _upsert_album_season(
        self,
        title: Title,
        album_key: str,
        title_key: str,
        *,
        force: bool = False,
    ) -> None:
        season = Season.get_from_memory(self.session, title, album_key)
        if self._season_is_outdated(season, title_key, force=force):
            album_file = self.music_playlist_file(album_key)
            data_timestamps = self._season_files_data_timestamps(album_key, title_key)
            season = Season(
                key=album_key,
                name=album_file.title(),
                url=playlist_url(album_key),
                image_url=album_file.image_url(),
                thumbnail_url=album_file.image_url(),
                data_timestamp=max(data_timestamps),
                title_id=title.id,
            ).upsert(title, season)
            season.set_update_at(
                staggered_monthly_update_at(album_key, min(data_timestamps)),
            )
        self._upsert_episodes(season, title_key, force=force)


# from __future__ import annotations

# from datetime import timedelta
# from typing import TYPE_CHECKING, Any, override

# from app.seasons.models import Season
# from app.titles.models import Title
# from plugins.YouTube.importer import YouTubeImporter
# from plugins.YouTube.utils import (
#     channel_url,
#     get_first_item,
#     image_url,
#     is_an_album,
#     playlist_url,
#     thumbnail_url,
#     topic_release_keys_from_file,
# )

# if TYPE_CHECKING:
#     from collections.abc import Sequence

#     from app.sources.models import Source
#     from plugins.utils.base_plugin.files import BaseFile
#     from plugins.YouTube.files import MusicPlaylist


# # TODO: Validate
# class YouTubeMusicSeasons(YouTubeImporter):
#     # TODO: Validate
#     def _with_album_seasons(self, season_keys: list[str], title_key: str) -> list[str]:
#         # An album playlist is auto-generated and listed by no channel, so it is only
#         # ever added by an importing URL naming it and then always kept.
#         return season_keys + [
#             key
#             for key in self._album_season_keys_from_database(title_key)
#             if key not in season_keys
#         ]

#     # TODO: Validate
#     def _album_season_keys_from_database(self, title_key: str) -> list[str]:
#         season_keys: list[str] = []
#         if self.parsed_url and self.parsed_url.album_playlist_key:
#             season_keys.append(self.parsed_url.album_playlist_key)

#         existing_title = self._preload_title(
#             title_key,
#             preload_seasons=True,
#         ).one_or_none()
#         if existing_title:
#             season_keys.extend(
#                 season.key
#                 for season in existing_title.seasons
#                 if is_an_album(season.key) and season.key not in season_keys
#             )
#         return season_keys

#     # TODO: Validate
#     def _upsert_seasons_album(
#         self,
#         title: Title,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> None:
#         for season_key in self._album_season_keys_from_database(title_key):
#             music_playlist = self.music_playlist_file(season_key)
#             self._upsert_season_music(
#                 title,
#                 season_key,
#                 title_key,
#                 music_playlist.title(),
#                 force=force,
#             )

#     # TODO: Validate
#     def _upsert_season_music(
#         self,
#         title: Title,
#         season_key: str,
#         title_key: str,
#         name: str | None,
#         *,
#         force: bool = False,
#     ) -> None:
#         season = Season.get_from_memory(self.session, title, season_key)
#         if self._season_is_outdated(season, title_key, force=force):
#             music_playlist = self.music_playlist_file(season_key)
#             data_timestamps = self._season_files_data_timestamps(season_key, title_key)
#             season = Season(
#                 key=season_key,
#                 name=name,
#                 url=playlist_url(season_key),
#                 image_url=music_playlist.image_url(),
#                 thumbnail_url=music_playlist.image_url(),
#                 data_timestamp=max(data_timestamps),
#                 title_id=title.id,
#             ).upsert(title, season)
#             season.set_update_at(
#                 min(data_timestamps) + timedelta(days=365),
#             )
#         self._upsert_episodes(season, title_key, force=force)

#     # TODO: Validate
#     @staticmethod
#     def _music_name(music_playlist: MusicPlaylist) -> str | None:
#         title = music_playlist.title()
#         artists = music_playlist.artists()
#         if not title or not artists:
#             return title
#         return f"{title} - {', '.join(artists)}"


# # TODO: Validate
# class YouTubeMusicImporter(YouTubeMusicSeasons):
#     # TODO: Validate
#     @override
#     def _season_files(
#         self,
#         season_key: str,
#         title_key: str,
#     ) -> Sequence[BaseFile[Any]]:
#         return [self.music_playlist_file(season_key)]

#     # TODO: Validate
#     @override
#     def _season_episode_keys_from_file(self, season_key: str) -> list[str]:
#         return self.music_playlist_file(season_key).track_keys()

#     # TODO: Validate
#     @override
#     def _get_episode_number(
#         self,
#         episode_key: str,
#         season_key: str,
#         title_key: str,
#     ) -> int | None:
#         return self._episode_number_from_file_order(episode_key, season_key)

#     # TODO: Validate
#     @override
#     def _upsert_episodes(
#         self,
#         season: Season,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> None:
#         self._upsert_episodes_in_file_order(season, title_key, force=force)


# # TODO: Validate
# class YouTubeAlbumImporter(YouTubeMusicImporter):
#     # TODO: Validate
#     @override
#     def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
#         return [self.music_playlist_file(title_key)]

#     # TODO: Validate
#     @override
#     def _season_keys_from_title_files(self, title_key: str) -> list[str]:
#         return [title_key]

#     # TODO: Validate
#     @override
#     def _upsert_title(
#         self,
#         source: Source,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> Title:
#         music_playlist = self.music_playlist_file(title_key)
#         source = self.source

#         title = Title.get_from_memory(self.session, source, title_key)
#         if self._title_is_outdated(title, force=force):
#             data_timestamps = self._title_files_data_timestamps(title_key)
#             title = Title(
#                 key=title_key,
#                 name=self._music_name(music_playlist),
#                 url=playlist_url(title_key),
#                 media_type=f"YouTube {music_playlist.release_type() or 'Album'}",
#                 image_url=music_playlist.image_url(),
#                 thumbnail_url=music_playlist.image_url(),
#                 data_timestamp=max(data_timestamps),
#                 source_id=source.id,
#             ).upsert(source, title)
#             title.set_update_at(
#                 min(data_timestamps) + timedelta(days=365),
#             )

#         self._upsert_season_music(
#             title,
#             title_key,
#             title_key,
#             self._music_name(music_playlist),
#             force=force,
#         )
#         self._soft_delete_missing_seasons_and_episodes(title_key)

#         return title


# # TODO: Validate
# class YouTubeTopicImporter(YouTubeMusicImporter):
#     # TODO: Validate
#     @override
#     def _title_files(self, title_key: str) -> Sequence[BaseFile[Any]]:
#         # A Topic channel's releases are the only thing it lists, and the API says
#         # nothing about them, so they are read off the channel's page instead of
#         # out of the playlists it owns.
#         return [
#             self.topic_file(title_key),
#             self.channel_by_channel_id_file(title_key),
#         ]

#     # TODO: Validate
#     @override
#     def _season_keys_from_title_files(self, title_key: str) -> list[str]:
#         # A Topic channel has one season for every release it lists.
#         return self._with_album_seasons(
#             topic_release_keys_from_file(self.topic_file(title_key)),
#             title_key,
#         )

#     # TODO: Validate
#     @override
#     def _upsert_title(
#         self,
#         source: Source,
#         title_key: str,
#         *,
#         force: bool = False,
#     ) -> Title:
#         """Upsert the musician a Topic channel is generated for.

#         A release of theirs is a season of this title rather than a title of its
#         own, which is what makes importing the channel import all of their music
#         the way importing a channel imports all of its playlists.
#         """
#         source = self.source

#         title = Title.get_from_memory(self.session, source, title_key)
#         if self._title_is_outdated(title, force=force):
#             channel_item = get_first_item(
#                 self.channel_by_channel_id_file(title_key).parsed().items,
#             )
#             data_timestamps = self._title_files_data_timestamps(title_key)
#             title = Title(
#                 key=title_key,
#                 name=channel_item.snippet.title,
#                 url=channel_url(title_key),
#                 media_type="YouTube Artist",
#                 image_url=image_url(channel_item.snippet.thumbnails),
#                 thumbnail_url=thumbnail_url(channel_item.snippet.thumbnails),
#                 data_timestamp=max(data_timestamps),
#                 # A musician only changes when they put something out.
#                 update_at=min(data_timestamps) + timedelta(days=365),
#                 source_id=source.id,
#             ).upsert(source, title)
#             title.set_update_at(None)

#         for season_key in self._season_keys_from_title_files(title_key):
#             music_playlist = self.music_playlist_file(season_key)
#             self._upsert_season_music(
#                 title,
#                 season_key,
#                 title_key,
#                 music_playlist.title(),
#                 force=force,
#             )
#         self._soft_delete_missing_seasons_and_episodes(title_key)

#         return title
