# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, ClassVar, Literal, override

from chirashi import Chirashi
from chirashi.artist import Artist as ArtistEndpoint
from chirashi.artist.models import ArtistModel
from chirashi.artist_concerts import ArtistConcerts as ArtistConcertsEndpoint
from chirashi.artist_concerts.models import ArtistConcertsModel
from chirashi.artist_music_videos import ArtistMusicVideos as ArtistMusicVideosEndpoint
from chirashi.artist_music_videos.models import ArtistMusicVideosModel
from chirashi.browse_music import BrowseMusic as BrowseMusicEndpoint
from chirashi.browse_music.models import BrowseMusicModel
from chirashi.browse_series import Browse as BrowseSeriesEndpoint
from chirashi.browse_series.models import BrowseSeriesModel
from chirashi.concert import Concert as ConcertEndpoint
from chirashi.concert.models import ConcertModel
from chirashi.exceptions import (
    ArtistNotFoundError,
    ConcertNotFoundError,
    EpisodeNotFoundError,
    MusicVideoNotFoundError,
    SeriesNotFoundError,
)
from chirashi.music_video import MusicVideo as MusicVideoEndpoint
from chirashi.music_video.models import MusicVideoModel
from chirashi.objects import Objects as ObjectsEndpoint
from chirashi.objects.models import ObjectsModel
from chirashi.season_episodes import SeasonEpisodes as SeasonEpisodesEndpoint
from chirashi.season_episodes.models import SeasonEpisodesModel
from chirashi.seasons import Seasons as SeasonsEndpoint
from chirashi.seasons.models import SeasonsModel
from chirashi.series import Series as SeriesEndpoint
from chirashi.series.models import SeriesModel

from app.files.models import File
from plugins.Crunchyroll.music_keys import (
    MusicCategory,
    is_music_episode_key,
    is_music_season_key,
    is_music_show_key,
    music_episode_category,
)
from plugins.utils.base_plugin import BasePlugin
from plugins.utils.base_plugin.files import BaseFile, EndpointFile, PagedEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def chirashi() -> Chirashi:
    """Return a cached Chirashi client."""
    return Chirashi(get_around_client=get_around_client())


# TODO: Validate
class Series(EndpointFile[SeriesModel]):
    """Data for a show."""

    API_ENDPOINT: ClassVar[SeriesEndpoint] = chirashi().series

    # Occurs when a user puts in an invalid series URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid series_id {self.unique_identifier}"


# TODO: Validate
class Objects(EndpointFile[ObjectsModel]):
    """Data for an episode."""

    API_ENDPOINT: ClassVar[ObjectsEndpoint] = chirashi().objects

    # Occurs when a user puts in an invalid episode URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, EpisodeNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid episode_id {self.unique_identifier}"


# TODO: Validate
class Seasons(EndpointFile[SeasonsModel]):
    """Data for the seasons."""

    API_ENDPOINT: ClassVar[SeasonsEndpoint] = chirashi().seasons


# TODO: Validate
class SeasonEpisodes(EndpointFile[SeasonEpisodesModel]):
    """Data for the episodes in a season."""

    API_ENDPOINT: ClassVar[SeasonEpisodesEndpoint] = chirashi().season_episodes


# TODO: Validate
class BrowseSeries(PagedEndpointFile[BrowseSeriesModel]):
    """Data for recently aired shows."""

    IMMUTABLE = True  # Files are stamped with a datetime

    API_ENDPOINT: ClassVar[BrowseSeriesEndpoint] = chirashi().browse_series

    # TODO: Validate
    @override
    def _download_pages(self) -> list[str]:
        return self.API_ENDPOINT.download_until_datetime(
            end_datetime=self.identifier_datetime(),
        )


# TODO: Validate
class Artist(EndpointFile[ArtistModel]):
    """Data for an artist."""

    API_ENDPOINT: ClassVar[ArtistEndpoint] = chirashi().artist

    # Occurs when a user puts in an invalid artist URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ArtistNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid artist_id {self.unique_identifier}"


# TODO: Validate
class ArtistMusicVideos(EndpointFile[ArtistMusicVideosModel]):
    """Data for an artist's music videos."""

    API_ENDPOINT: ClassVar[ArtistMusicVideosEndpoint] = chirashi().artist_music_videos


# TODO: Validate
class ArtistConcerts(EndpointFile[ArtistConcertsModel]):
    """Data for an artist's concerts."""

    API_ENDPOINT: ClassVar[ArtistConcertsEndpoint] = chirashi().artist_concerts


# TODO: Validate
class MusicVideo(EndpointFile[MusicVideoModel]):
    """Data for a music video."""

    API_ENDPOINT: ClassVar[MusicVideoEndpoint] = chirashi().music_video

    # Occurs when a user puts in an invalid music video URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MusicVideoNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid music_video_id {self.unique_identifier}"


# TODO: Validate
class Concert(EndpointFile[ConcertModel]):
    """Data for a concert."""

    API_ENDPOINT: ClassVar[ConcertEndpoint] = chirashi().concert

    # Occurs when a user puts in an invalid concert URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ConcertNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid concert_id {self.unique_identifier}"


# TODO: Validate
class BrowseMusic(PagedEndpointFile[BrowseMusicModel]):
    """Data for all of the music."""

    IMMUTABLE = True

    API_ENDPOINT: ClassVar[BrowseMusicEndpoint] = chirashi().browse_music

    # Music seems to be ordered randomly so downloading all of it is required.
    # TODO: Validate
    @override
    def _download_pages(self) -> list[str]:
        return self.API_ENDPOINT.download_all()


# TODO: Validate
class FileMixin(BasePlugin, register=False):
    """File mixin."""

    # TODO: Validate
    @classmethod
    @override
    def _plugin_wide_files(cls) -> tuple[type[BaseFile[Any]], ...]:
        return (BrowseSeries, BrowseMusic)

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
            season_data.id for season_data in self.seasons_file(show_key).parsed().data
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
                episode.id
                for episode in self.season_episodes_file(season_key).parsed().data
            ]
        return episode_keys

    # TODO: Validate
    def _music_episode_keys(self, season_key: str, show_key: str) -> list[str]:
        listing = self.artist_concerts_or_artist_music_videos_file(
            show_key,
            MusicCategory(season_key),
        ).parsed()
        return [datum.id for datum in listing.data]

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
