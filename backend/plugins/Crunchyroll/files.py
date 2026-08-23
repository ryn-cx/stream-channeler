# TODO: Validate
from abc import ABC
from collections.abc import Sequence
from datetime import datetime
from typing import Any, Literal, override

from app.files.models import File
from plugins.Crunchyroll import api
from plugins.Crunchyroll.music_keys import (
    MusicCategory,
    is_music_episode_key,
    is_music_season_key,
    is_music_show_key,
    music_episode_category,
)
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointJSON


# TODO: Validate
class CrunchyrollJSON(EndpointJSON[dict[str, Any]], ABC):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> dict[str, Any]:
        return self.raise_if_not_is_instance(raw, dict)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)


# TODO: Validate
class CrunchyrollListJSON(EndpointJSON[list[dict[str, Any]]], ABC):
    # TODO: Validate
    @override
    def _parse(self, raw: Any) -> list[dict[str, Any]]:
        return self.raise_if_not_is_instance(raw, list)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            try:
                response = self._fetch()
            except Exception as error:
                if not self._is_acceptable_error(error):
                    raise
                self.write(None, self.acceptable_error_extra_value())
            else:
                self.write(response)


# TODO: Validate
class Series(CrunchyrollJSON):
    """Data for a show."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.series(self.unique_identifier)

    # Occurs when a user puts in an invalid series URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.SeriesNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid series_id {self.unique_identifier}"


# TODO: Validate
class Objects(CrunchyrollJSON):
    """Data for an episode."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.objects(self.unique_identifier)

    # Occurs when a user puts in an invalid episode URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.EpisodeNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid episode_id {self.unique_identifier}"


# TODO: Validate
class Seasons(CrunchyrollJSON):
    """Data for the seasons."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.seasons(self.unique_identifier)


# TODO: Validate
class SeasonEpisodes(CrunchyrollJSON):
    """Data for the episodes in a season."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.season_episodes(self.unique_identifier)


# TODO: Validate
class BrowseSeries(CrunchyrollListJSON):
    """Data for recently aired shows."""

    IMMUTABLE = True  # Files are stamped with a datetime

    # Use browse_series_until_datetime instead of browse_series so the new file
    # includes entries up to the previous file.
    # TODO: Validate
    @override
    def _fetch(self) -> list[dict[str, Any]]:
        return api.browse_series_until_datetime(
            end_datetime=self.identifier_datetime(),
        )


# TODO: Validate
class Search(CrunchyrollJSON):
    """Data for search results."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.search(self.unique_identifier)


# TODO: Validate
class Artist(CrunchyrollJSON):
    """Data for an artist."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.artist(self.unique_identifier)

    # Occurs when a user puts in an invalid artist URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.ArtistNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid artist_id {self.unique_identifier}"


# TODO: Validate
class ArtistMusicVideos(CrunchyrollJSON):
    """Data for an artist's music videos."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.artist_music_videos(self.unique_identifier)


# TODO: Validate
class ArtistConcerts(CrunchyrollJSON):
    """Data for an artist's concerts."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.artist_concerts(self.unique_identifier)


# TODO: Validate
class MusicVideo(CrunchyrollJSON):
    """Data for a music video."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.music_video(self.unique_identifier)

    # Occurs when a user puts in an invalid music video URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.MusicVideoNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid music_video_id {self.unique_identifier}"


# TODO: Validate
class Concert(CrunchyrollJSON):
    """Data for a concert."""

    # TODO: Validate
    @override
    def _fetch(self) -> dict[str, Any]:
        return api.concert(self.unique_identifier)

    # Occurs when a user puts in an invalid concert URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, api.ConcertNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid concert_id {self.unique_identifier}"


# TODO: Validate
class BrowseMusic(CrunchyrollListJSON):
    """Data for all of the music."""

    IMMUTABLE = True

    # Music seems to be ordered randomly so downloading all of it is required.
    # TODO: Validate
    @override
    def _fetch(self) -> list[dict[str, Any]]:
        return api.browse_music_all()


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """File mixin."""

    _PLUGIN_WIDE_FILES = (BrowseSeries, BrowseMusic)

    # TODO: Validate
    def series_file(self, show_key: str) -> Series:
        """Return data for a show."""
        return self._file(Series, show_key)

    # TODO: Validate
    def objects_file(self, episode_key: str) -> Objects:
        """Return data for an episode."""
        return self._file(Objects, episode_key)

    # TODO: Validate
    def seasons_file(self, show_key: str) -> Seasons:
        """Return data for the seasons."""
        return self._file(Seasons, show_key)

    # TODO: Validate
    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        """Return data for the episodes in a season."""
        return self._file(SeasonEpisodes, season_key)

    # TODO: Validate
    def browse_series_file(
        self,
        browse: datetime | File | Literal["Initial"],
    ) -> BrowseSeries:
        """Return data for recently aired shows."""
        if isinstance(browse, File):
            browse = BrowseSeries.file_key_to_unique_identifier(browse.key)
        return self._file(BrowseSeries, str(browse))

    # TODO: Validate
    def search_file(self, query: str) -> Search:
        """Return data for search results."""
        return self._file(Search, query)

    # TODO: Validate
    def artist_file(self, artist_id: str) -> Artist:
        """Return data for an artist."""
        return self._file(Artist, artist_id)

    # TODO: Validate
    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        """Return data for an artist's music videos."""
        return self._file(ArtistMusicVideos, artist_id)

    # TODO: Validate
    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        """Return data for an artist's concerts."""
        return self._file(ArtistConcerts, artist_id)

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
    def music_video_file(self, music_video_id: str) -> MusicVideo:
        """Return data for a music video."""
        return self._file(MusicVideo, music_video_id)

    # TODO: Validate
    def concert_file(self, concert_id: str) -> Concert:
        """Return data for a concert."""
        return self._file(Concert, concert_id)

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
    def browse_music_file(
        self,
        browse: datetime | File | Literal["Initial"],
    ) -> BrowseMusic:
        """Return data for all of the music."""
        if isinstance(browse, File):
            browse = BrowseMusic.file_key_to_unique_identifier(browse.key)
        return self._file(BrowseMusic, str(browse))

    # TODO: Validate
    def find_newest_browse_music_file(self) -> BrowseMusic | None:
        """Return newest data for all of the music, or None when there is none."""
        if file := self.preload_latest_file(BrowseMusic):
            return self.browse_music_file(file)
        return None

    # TODO: Validate
    def get_newest_music_browse_file(self) -> BrowseMusic:
        """Return the newest music browse file. Raises if one does not exist."""
        if file := self.find_newest_browse_music_file():
            return file

        msg = "No music browse file found."
        raise FileNotFoundError(msg)

    # TODO: Validate
    def _music_source_files(self) -> Sequence[BrowseMusic]:
        """Return the `Source` files for Crunchyroll music."""
        return [self.get_newest_music_browse_file()]

    # TODO: Validate
    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        """Return the `Source` files for Crunchyroll video."""
        return [self.get_newest_browse_series_file()]

    # TODO: Validate
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if is_music_show_key(show_key):
            return [
                # Required to detect changes to the artist.
                self.artist_file(show_key),
                # Required to detect new music videos and concerts.
                self.artist_music_videos_file(show_key),
                self.artist_concerts_file(show_key),
            ]
        return [
            # Required to detect new seasons.
            self.seasons_file(show_key),
            # Required to detect changes to the show.
            self.series_file(show_key),
        ]

    # TODO: Validate
    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if is_music_season_key(season_key):
            category = MusicCategory(season_key)
            return [
                # Required to detect new music videos or concerts.
                self.artist_concerts_or_artist_music_videos_file(show_key, category),
                # Required to detect changes to the artist.
                self.artist_file(show_key),
            ]
        return [
            # Required to detect new episodes.
            self.season_episodes_file(season_key),
            # Required to detect changes to the season.
            self.seasons_file(show_key),
        ]

    # TODO: Validate
    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if is_music_episode_key(episode_key):
            # A music video or concert carries its own details, unlike a series
            # episode which is read out of its season's listing.
            return [self.concert_or_music_video_file(episode_key)]
        return [self.season_episodes_file(season_key)]

    # TODO: Validate
    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if is_music_show_key(show_key):
            # Both categories are always seasons of the artist, even while one is
            # empty, so a first release into it is a new episode rather than a
            # new season the show has to notice.
            return [category.value for category in MusicCategory]
        return [
            season_data["id"]
            for season_data in self.seasons_file(show_key).parsed()["data"]
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            if is_music_season_key(season_key):
                episode_keys += self._music_episode_keys(season_key, show_key)
                continue
            episode_keys += [
                episode["id"]
                for episode in self.season_episodes_file(season_key).parsed()["data"]
            ]
        return episode_keys

    # TODO: Validate
    def _music_episode_keys(self, season_key: str, show_key: str) -> list[str]:
        listing = self.artist_concerts_or_artist_music_videos_file(
            show_key,
            MusicCategory(season_key),
        ).parsed()
        return [datum["id"] for datum in listing["data"]]

    # TODO: Validate
    def find_newest_browse_series_file(self) -> BrowseSeries | None:
        """Return newest browse series file or None if one does not exist."""
        if file := self.preload_latest_file(BrowseSeries):
            return self.browse_series_file(file)
        return None

    # TODO: Validate
    def get_newest_browse_series_file(self) -> BrowseSeries:
        """Return newest browse series file or raises if one does not exist.

        Raise:
            FileNotFoundError: If no browse file exists.
        """
        if file := self.find_newest_browse_series_file():
            return file

        msg = "No browse file found."
        raise FileNotFoundError(msg)
