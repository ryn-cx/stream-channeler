# TODO: Validate
from collections.abc import Sequence
from datetime import datetime
from functools import cache
from typing import Any, Literal, overload, override

from chirashi import Chirashi
from chirashi.artist import models as artist_models
from chirashi.artist_concerts import models as artist_concerts_models
from chirashi.artist_music_videos import models as artist_music_videos_models
from chirashi.browse_music import models as browse_music_models
from chirashi.browse_series import models as browse_series_models
from chirashi.concert import models as concert_models
from chirashi.exceptions import (
    ArtistNotFoundError,
    ConcertNotFoundError,
    EpisodeNotFoundError,
    MusicVideoNotFoundError,
    SeriesNotFoundError,
)
from chirashi.music_video import models as music_video_models
from chirashi.objects import models as objects_models
from chirashi.search import models as search_models
from chirashi.season_episodes import models as episodes_models
from chirashi.seasons import models as seasons_models
from chirashi.series import models as series_models

from app.files.models import File
from app.utils import tz_datetime
from plugins.Crunchyroll.music_keys import (
    MUSIC_CATEGORIES,
    MusicCategory,
    is_artist_show_key,
    is_music_episode_key,
    is_music_season_key,
    music_episode_key,
    music_season_key,
    parse_artist_show_key,
    parse_music_episode_key,
    parse_music_season_key,
)
from plugins.TMDB.mixin import TMDBMixin
from plugins.utils.base_plugin.files import GAPIJSON, BaseFile, GAPIListJSON
from plugins.utils.get_around_client import get_around_client


@cache
def chirashi() -> Chirashi:
    """Returns a cached Chirashi client."""
    return Chirashi(get_around_client=get_around_client())


class Series(GAPIJSON[series_models.SeriesModel]):
    """Series file."""

    API_ENDPOINT = chirashi().series

    # Occurs when a user puts in an invalid series URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid series_id {self.unique_identifier}"


class Objects(GAPIJSON[objects_models.ObjectsModel]):
    """Objects file."""

    API_ENDPOINT = chirashi().objects

    # Occurs when a user puts in an invalid episode URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, EpisodeNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid episode_id {self.unique_identifier}"


class Seasons(GAPIJSON[seasons_models.SeasonsModel]):
    """Seasons file."""

    API_ENDPOINT = chirashi().seasons


class SeasonEpisodes(GAPIJSON[episodes_models.SeasonEpisodesModel]):
    """Season episodes file."""

    API_ENDPOINT = chirashi().season_episodes


class BrowseSeries(GAPIListJSON[browse_series_models.BrowseSeriesModel]):
    """Browse series file."""

    IMMUTABLE = True
    API_ENDPOINT = chirashi().browse_series

    # Need to use download_and_parse_until_datetime instead of download_and_parse so the
    # new BrowseSeriesModel includes entries up to the previous BrowseSeriesModel.
    @override
    def _get(self) -> list[browse_series_models.BrowseSeriesModel]:
        return chirashi().browse_series.download_and_parse_until_datetime(
            end_datetime=tz_datetime.fromisoformat(self.unique_identifier),
        )

    def extract_datums(self) -> list[browse_series_models.Datum]:
        return chirashi().browse_series.extract_data(self.parsed())


class Search(GAPIJSON[search_models.SearchModel]):
    """Search file."""

    API_ENDPOINT = chirashi().search


class Artist(GAPIJSON[artist_models.ArtistModel]):
    """Artist file."""

    API_ENDPOINT = chirashi().artist

    # Occurs when a user puts in an invalid artist URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ArtistNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid artist_id {self.unique_identifier}"


class ArtistMusicVideos(GAPIJSON[artist_music_videos_models.ArtistMusicVideosModel]):
    """Artist music videos file."""

    API_ENDPOINT = chirashi().artist_music_videos

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ArtistNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid artist_id {self.unique_identifier}"


class ArtistConcerts(GAPIJSON[artist_concerts_models.ArtistConcertsModel]):
    """Artist concerts file."""

    API_ENDPOINT = chirashi().artist_concerts

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ArtistNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid artist_id {self.unique_identifier}"


class MusicVideo(GAPIJSON[music_video_models.MusicVideoModel]):
    """Music video file."""

    API_ENDPOINT = chirashi().music_video

    # Occurs when a user puts in an invalid music video URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MusicVideoNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid music_video_id {self.unique_identifier}"


class Concert(GAPIJSON[concert_models.ConcertModel]):
    """Concert file."""

    API_ENDPOINT = chirashi().concert

    # Occurs when a user puts in an invalid concert URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ConcertNotFoundError)

    @override
    def acceptable_error_extra_value(self) -> str:
        return f"Invalid concert_id {self.unique_identifier}"


class BrowseMusic(GAPIListJSON[browse_music_models.BrowseMusicModel]):
    """Browse music file.

    The music catalogue is browsed by artist and offers no cutoff parameter, so
    every page is downloaded rather than only the ones newer than the previous
    file. It is small next to the series catalogue and only read monthly.
    """

    IMMUTABLE = True
    API_ENDPOINT = chirashi().browse_music

    @override
    def _get(self) -> list[browse_music_models.BrowseMusicModel]:
        return chirashi().browse_music.download_and_parse_all()

    def extract_datums(self) -> list[browse_music_models.Datum]:
        return chirashi().browse_music.extract_data(self.parsed())


class FileMixin(TMDBMixin, register=False):
    # The browse listing belongs to the source, so every show reads the same one.
    _PLUGIN_WIDE_FILES = (BrowseSeries, BrowseMusic)

    def series_file(self, show_key: str) -> Series:
        """Returns Series file."""
        return self._file(Series, show_key)

    def objects_file(self, episode_key: str) -> Objects:
        """Returns Objects file."""
        return self._file(Objects, episode_key)

    def seasons_file(self, show_key: str) -> Seasons:
        """Returns Seasons file."""
        return self._file(Seasons, show_key)

    def season_episodes_file(self, season_key: str) -> SeasonEpisodes:
        """Returns SeasonEpisodes file."""
        return self._file(SeasonEpisodes, season_key)

    def browse_series_file(self, browse_datetime: datetime) -> BrowseSeries:
        """Returns BrowseSeries file."""
        return self._file(BrowseSeries, str(browse_datetime))

    def browse_series_file_from_record(self, record: File) -> BrowseSeries:
        """Returns the BrowseSeries file for an existing `File` record."""
        return self._file(
            BrowseSeries,
            BrowseSeries.file_key_to_unique_identifier(record.key),
        )

    def search_file(self, query: str) -> Search:
        """Returns Search file."""
        return self._file(Search, query)

    def artist_file(self, artist_id: str) -> Artist:
        """Returns Artist file."""
        return self._file(Artist, artist_id)

    def artist_music_videos_file(self, artist_id: str) -> ArtistMusicVideos:
        """Returns ArtistMusicVideos file."""
        return self._file(ArtistMusicVideos, artist_id)

    def artist_concerts_file(self, artist_id: str) -> ArtistConcerts:
        """Returns ArtistConcerts file."""
        return self._file(ArtistConcerts, artist_id)

    def artist_category_file(
        self,
        artist_id: str,
        category: MusicCategory,
    ) -> ArtistMusicVideos | ArtistConcerts:
        """Returns the listing file for one of an artist's categories."""
        if category == "concert":
            return self.artist_concerts_file(artist_id)
        return self.artist_music_videos_file(artist_id)

    def music_video_file(self, music_video_id: str) -> MusicVideo:
        """Returns MusicVideo file."""
        return self._file(MusicVideo, music_video_id)

    def concert_file(self, concert_id: str) -> Concert:
        """Returns Concert file."""
        return self._file(Concert, concert_id)

    def music_file(self, episode_key: str) -> MusicVideo | Concert:
        """Returns the file a music `Episode` key is read from."""
        category, video_id = parse_music_episode_key(episode_key)
        if category == "concert":
            return self.concert_file(video_id)
        return self.music_video_file(video_id)

    def browse_music_file(self, browse_datetime: datetime) -> BrowseMusic:
        """Returns BrowseMusic file."""
        return self._file(BrowseMusic, str(browse_datetime))

    def browse_music_file_from_record(self, record: File) -> BrowseMusic:
        """Returns the BrowseMusic file for an existing `File` record."""
        return self._file(
            BrowseMusic,
            BrowseMusic.file_key_to_unique_identifier(record.key),
        )

    def find_newest_music_browse_file(
        self,
        *,
        is_completed: bool = False,
    ) -> BrowseMusic | None:
        """Returns newest BrowseMusic file."""
        extra = "Completed" if is_completed else None
        if file := self.preload_latest_file(BrowseMusic, extra=extra):
            return self.browse_music_file_from_record(file)
        return None

    def _music_source_files(self) -> Sequence[BrowseMusic]:
        """Returns the files the music `Source` is dated by."""
        if file := self.find_newest_music_browse_file(is_completed=True):
            return [file]
        return []

    @override
    def _source_files(self) -> Sequence[BrowseSeries]:
        if file := self.find_newest_browse_file(is_completed=True):
            return [file]
        return []

    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        if is_artist_show_key(show_key):
            artist_id = parse_artist_show_key(show_key)
            return [
                # Required to detect changes to the artist.
                self.artist_file(artist_id),
                # Required to detect new music videos and concerts.
                self.artist_music_videos_file(artist_id),
                self.artist_concerts_file(artist_id),
            ]
        return self._append_tmdb_show_file(
            [
                # Required to detect new seasons.
                self.seasons_file(show_key),
                # Required to detect changes to the show.
                self.series_file(show_key),
            ],
            show_key,
        )

    @override
    def _season_files(
        self,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        if is_music_season_key(season_key):
            artist_id, category = parse_music_season_key(season_key)
            return [
                # Required to detect new music videos or concerts.
                self.artist_category_file(artist_id, category),
                # Required to detect changes to the artist.
                self.artist_file(artist_id),
            ]
        return self._append_tmdb_season_file(
            [
                # Required to detect new episodes.
                self.season_episodes_file(season_key),
                # Required to detect changes to the season.
                self.seasons_file(show_key),
            ],
            season_key,
            show_key,
        )

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
            return [self.music_file(episode_key)]
        return self._append_tmdb_episode_file(
            [self.season_episodes_file(season_key)],
            episode_key,
            season_key,
            show_key,
        )

    @override
    def _season_keys_from_file(self, show_key: str) -> list[str]:
        if is_artist_show_key(show_key):
            artist_id = parse_artist_show_key(show_key)
            # Both categories are always seasons of the artist, even while one is
            # empty, so a first release into it is a new episode rather than a
            # new season the show has to notice.
            return [
                music_season_key(artist_id, category) for category in MUSIC_CATEGORIES
            ]
        return [
            season_data.id for season_data in self.seasons_file(show_key).parsed().data
        ]

    @override
    def _episode_keys_from_file(
        self,
        season_keys: str | list[str],
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            if is_music_season_key(season_key):
                episode_keys += self._music_episode_keys(season_key)
                continue
            episode_keys += [
                episode.id
                for episode in self.season_episodes_file(season_key).parsed().data
            ]
        return episode_keys

    def _music_episode_keys(self, season_key: str) -> list[str]:
        artist_id, category = parse_music_season_key(season_key)
        listing = self.artist_category_file(artist_id, category).parsed()
        return [music_episode_key(category, datum.id) for datum in listing.data]

    @overload
    def find_newest_browse_file(
        self,
        *,
        is_completed: bool = ...,
        strict: Literal[True],
    ) -> BrowseSeries: ...

    @overload
    def find_newest_browse_file(
        self,
        *,
        is_completed: bool = ...,
        strict: Literal[False] = ...,
    ) -> BrowseSeries | None: ...

    def find_newest_browse_file(
        self,
        *,
        is_completed: bool = False,
        strict: bool = False,
    ) -> BrowseSeries | None:
        """Returns newest BrowseSeries file."""
        extra = "Completed" if is_completed else None
        if file := self.preload_latest_file(BrowseSeries, extra=extra):
            return self.browse_series_file_from_record(file)

        if strict:
            msg = "No browse file found."
            raise FileNotFoundError(msg)
        return None
