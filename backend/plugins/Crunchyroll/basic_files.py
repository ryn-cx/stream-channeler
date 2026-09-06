# TODO: Validate
from __future__ import annotations

from plugins.Crunchyroll.files import (
    Artist,
    ArtistConcerts,
    ArtistMusicVideos,
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
from plugins.utils.base_plugin.base import BasePlugin


class BasicFiles(BasePlugin):
    def search_file(self, query: str) -> Search:
        return self._file(Search, query)

    def series_file(self, show_key: str) -> Series:
        return self._file(Series, show_key)

    def objects_file(self, episode_key: str) -> Objects:
        return self._file(Objects, episode_key)

    def seasons_file(self, show_key: str) -> Seasons:
        return self._file(Seasons, show_key)

    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        return self._file(SeasonEpisodes, season_key)

    def artist_file(self, artist_id: str) -> Artist:
        return self._file(Artist, artist_id)

    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        return self._file(ArtistMusicVideos, artist_id)

    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        return self._file(ArtistConcerts, artist_id)

    def music_video_file(self, music_video_id: str) -> MusicVideo:
        return self._file(MusicVideo, music_video_id)

    def concert_file(self, concert_id: str) -> Concert:
        return self._file(Concert, concert_id)

    def catalogue_file(self) -> Catalogue:
        return self._file(Catalogue, "alphabetical")

    # TODO: Validate
    def _is_movie(self, show_key: str) -> bool:
        return self.series_file(show_key).is_movie()

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
