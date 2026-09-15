# TODO: Validate
from __future__ import annotations

from plugins.Crunchyroll.constants import CrunchyrollMusicCategory
from plugins.Crunchyroll.files import (
    Artist,
    ArtistConcerts,
    ArtistMusicVideos,
    Catalogue,
    Categories,
    Concert,
    MusicVideo,
    Objects,
    SeasonEpisodes,
    Seasons,
    Series,
    SimilarTo,
)
from plugins.Crunchyroll.utils import music_episode_category
from plugins.utils.base_plugin.base import BasePlugin


# TODO: Validate
class CrunchyrollBaseFiles(BasePlugin):
    # TODO: Validate
    def series_file(self, title_key: str) -> Series:
        return self._cached_file(Series, title_key)

    # TODO: Validate
    def categories_file(self, title_key: str) -> Categories:
        return self._cached_file(Categories, title_key)

    # TODO: Validate
    def similar_to_file(self, title_key: str) -> SimilarTo:
        return self._cached_file(SimilarTo, title_key)

    # TODO: Validate
    def objects_file(self, episode_key: str) -> Objects:
        return self._cached_file(Objects, episode_key)

    # TODO: Validate
    def seasons_file(self, title_key: str) -> Seasons:
        return self._cached_file(Seasons, title_key)

    # TODO: Validate
    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        return self._cached_file(SeasonEpisodes, season_key)

    # TODO: Validate
    def artist_file(self, artist_id: str) -> Artist:
        return self._cached_file(Artist, artist_id)

    # TODO: Validate
    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        return self._cached_file(ArtistMusicVideos, artist_id)

    # TODO: Validate
    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        return self._cached_file(ArtistConcerts, artist_id)

    # TODO: Validate
    def music_video_file(self, music_video_id: str) -> MusicVideo:
        return self._cached_file(MusicVideo, music_video_id)

    # TODO: Validate
    def concert_file(self, concert_id: str) -> Concert:
        return self._cached_file(Concert, concert_id)

    # TODO: Validate
    def catalogue_file(self) -> Catalogue:
        return self._cached_file(Catalogue, "alphabetical")

    # TODO: Validate
    def season_file(
        self,
        artist_id: str,
        category: CrunchyrollMusicCategory,
    ) -> ArtistMusicVideos | ArtistConcerts:
        """Return the ArtistMusicVideos or ArtistConcerts file based on the category.

        Each artist (Title) has two `Season`s, one for concerts and one for music
        videos. This function main purpose is to make sure the correct files are
        returned when getting all of the files for a specific season.
        """
        if category is CrunchyrollMusicCategory.CONCERT:
            return self.artist_concerts_file(artist_id)
        return self.artist_music_videos_file(artist_id)

    # TODO: Validate
    def concert_or_music_video_file(
        self,
        episode_key: str,
    ) -> MusicVideo | Concert:
        """Return the Concert or MusicVideo file based on the category.

        There are different files for concerts and music videos. This function main
        purpose is to make sure the correct files are returned when getting all of the
        files for a specific episode.
        """
        if music_episode_category(episode_key) is CrunchyrollMusicCategory.CONCERT:
            return self.concert_file(episode_key)
        return self.music_video_file(episode_key)
