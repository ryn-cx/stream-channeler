# TODO: Validate
from __future__ import annotations

from typing import TYPE_CHECKING, Literal, override

from app.files.models import File
from plugins.Crunchyroll.files import (
    Artist,
    ArtistConcerts,
    ArtistMusicVideos,
    BrowseMusic,
    BrowseSeries,
    Catalogue,
    Concert,
    MusicVideo,
    Objects,
    Search,
    SeasonEpisodes,
    Seasons,
    Series,
)
from plugins.Crunchyroll.utils import MusicCategory, music_episode_category
from plugins.utils.base_plugin_v3.base import BasePlugin
from plugins.utils.base_plugin_v3.files import INITIAL_FILE_IDENTIFIER

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime

    from chirashi.series.models import Datum as SeriesDatum


class BasicFiles(BasePlugin):
    # TODO: Validate
    def search_file(self, query: str) -> Search:
        return self._file(Search, query)

    # TODO: Validate
    def series_file(self, show_key: str) -> Series:
        return self._file(Series, show_key)

    # TODO: Validate
    def objects_file(self, episode_key: str) -> Objects:
        return self._file(Objects, episode_key)

    # TODO: Validate
    def seasons_file(self, show_key: str) -> Seasons:
        return self._file(Seasons, show_key)

    # TODO: Validate
    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        return self._file(SeasonEpisodes, season_key)

    # TODO: Validate
    def artist_file(self, artist_id: str) -> Artist:
        return self._file(Artist, artist_id)

    # TODO: Validate
    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        return self._file(ArtistMusicVideos, artist_id)

    # TODO: Validate
    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        return self._file(ArtistConcerts, artist_id)

    # TODO: Validate
    def music_video_file(self, music_video_id: str) -> MusicVideo:
        return self._file(MusicVideo, music_video_id)

    # TODO: Validate
    def concert_file(self, concert_id: str) -> Concert:
        return self._file(Concert, concert_id)

    # TODO: Validate
    def catalogue_file(self) -> Catalogue:
        return self._file(Catalogue, "alphabetical")

    # TODO: Validate
    def _series_datum(self, show_key: str) -> SeriesDatum:
        return self.series_file(show_key).datum()

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self.series_file(show_key).is_movie()

    # TODO: Validate
    def browse_series_file(
        self,
        browse: datetime | File | Literal["Initial"],
    ) -> BrowseSeries:
        """Return data for recently aired shows."""
        if isinstance(browse, File):
            return self._file(
                BrowseSeries,
                BrowseSeries.file_to_unique_identifier(browse),
            )
        return self._file(BrowseSeries, str(browse))

    # TODO: Validate
    def browse_music_file(
        self,
        browse: datetime | File | Literal["Initial"],
    ) -> BrowseMusic:
        """Return data for all of the music."""
        if isinstance(browse, File):
            return self._file(
                BrowseMusic,
                BrowseMusic.file_to_unique_identifier(browse),
            )
        return self._file(BrowseMusic, str(browse))

    # TODO: Validate
    def artist_concerts_or_artist_music_videos_file(
        self,
        artist_id: str,
        category: MusicCategory,
    ) -> ArtistMusicVideos | ArtistConcerts:
        """Return either data for an artist's concerts or music videos.

        Concerts and Music Videos are saved in the database as separate seasons. This
        function makes it easier to share code between importing them by dynamically
        getting the correct file for the situation.
        """
        if category is MusicCategory.CONCERT:
            return self.artist_concerts_file(artist_id)
        return self.artist_music_videos_file(artist_id)

    # TODO: Validate
    def concert_or_music_video_file(self, episode_key: str) -> MusicVideo | Concert:
        """Return either data for a concert or a music video.

        Concerts and Music Videos are saved in the database as separate seasons. This
        function makes it easier to share code between importing them by dynamically
        getting the correct file for the situation.
        """
        if music_episode_category(episode_key) is MusicCategory.CONCERT:
            return self.concert_file(episode_key)
        return self.music_video_file(episode_key)

    # TODO: Validate
    def find_newest_browse_series_file(self) -> BrowseSeries | None:
        """Return newest browse series file or None if one does not exist."""
        if file := self.preload_latest_file(BrowseSeries):
            return self.browse_series_file(file)
        return None

    # TODO: Validate
    def find_newest_browse_music_file(self) -> BrowseMusic | None:
        """Return newest data for all of the music, or None when there is none."""
        if file := self.preload_latest_file(BrowseMusic):
            return self.browse_music_file(file)
        return None

    # TODO: Validate
    def newest_browse_series_file(self) -> BrowseSeries:
        if file := self.find_newest_browse_series_file():
            return file
        initial = self.browse_series_file(INITIAL_FILE_IDENTIFIER)
        initial.download_if_outdated()
        return initial

    # TODO: Validate
    def newest_browse_music_file(self) -> BrowseMusic:
        if file := self.find_newest_browse_music_file():
            return file
        initial = self.browse_music_file(INITIAL_FILE_IDENTIFIER)
        initial.download_if_outdated()
        return initial

    # TODO: Validate
    def _music_source_files(self) -> Sequence[BrowseMusic]:
        """Return the `Source` files for Crunchyroll music."""
        return [self.newest_browse_music_file()]

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        """Return the `Source` files for Crunchyroll video."""
        return [self.newest_browse_series_file()]
