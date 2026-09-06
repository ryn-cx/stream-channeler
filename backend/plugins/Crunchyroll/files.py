from abc import ABC
from datetime import UTC, datetime, timedelta
from functools import cache
from typing import override

from chirashi import Chirashi
from chirashi.artist import Artist as ArtistEndpoint
from chirashi.artist.models import ArtistModel
from chirashi.artist_concerts import ArtistConcerts as ArtistConcertsEndpoint
from chirashi.artist_concerts.models import ArtistConcertsModel
from chirashi.artist_music_videos import ArtistMusicVideos as ArtistMusicVideosEndpoint
from chirashi.artist_music_videos.models import ArtistMusicVideosModel
from chirashi.browse_music import BrowseMusic as BrowseMusicEndpoint
from chirashi.browse_music.models import BrowseMusicModel
from chirashi.browse_music.models import Datum as BrowseMusicDatum
from chirashi.browse_series import Browse as BrowseSeriesEndpoint
from chirashi.browse_series.models import BrowseSeriesModel
from chirashi.browse_series.models import Datum as BrowseSeriesDatum
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
from chirashi.search import Search as SearchEndpoint
from chirashi.search.models import SearchModel
from chirashi.season_episodes import SeasonEpisodes as SeasonEpisodesEndpoint
from chirashi.season_episodes.models import SeasonEpisodesModel
from chirashi.seasons import Seasons as SeasonsEndpoint
from chirashi.seasons.models import SeasonsModel
from chirashi.series import Series as SeriesEndpoint
from chirashi.series.models import SeriesModel

from app.utils import tz_datetime
from plugins.utils.base_plugin.files import EndpointFile, PagedEndpointFile
from plugins.utils.get_around_client import get_around_client


@cache
def chirashi() -> Chirashi:
    return Chirashi(get_around_client=get_around_client())


class Series(EndpointFile[SeriesModel]):
    @override
    def _endpoint(self) -> SeriesEndpoint:
        return chirashi().series

    # Occurs when a user puts in an invalid series URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


class Objects(EndpointFile[ObjectsModel]):
    """Episode information."""

    @override
    def _endpoint(self) -> ObjectsEndpoint:
        return chirashi().objects

    # Occurs when a user puts in an invalid episode URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, EpisodeNotFoundError)


class Seasons(EndpointFile[SeasonsModel]):
    @override
    def _endpoint(self) -> SeasonsEndpoint:
        return chirashi().seasons


class SeasonEpisodes(EndpointFile[SeasonEpisodesModel]):
    @override
    def _endpoint(self) -> SeasonEpisodesEndpoint:
        return chirashi().season_episodes


class BaseBrowseSeries(PagedEndpointFile[BrowseSeriesModel], ABC):
    @override
    def _endpoint(self) -> BrowseSeriesEndpoint:
        return chirashi().browse_series

    def datums(self) -> list[BrowseSeriesDatum]:
        return self._endpoint().extract_data(self.parsed())


class BrowseSeries(BaseBrowseSeries):
    @override
    def _download_pages(self) -> list[str]:
        return self._endpoint().download_until_datetime(
            end_datetime=self.identifier_datetime(),
        )


class Catalogue(BaseBrowseSeries):
    """Special BrowseSeries that contains all of the titles on Crunchyroll."""

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=7)

    @override
    def _download_pages(self) -> list[str]:
        return self._endpoint().download_until_datetime(
            end_datetime=datetime.min.replace(tzinfo=UTC),
            n=50,
            sort_by="alphabetical",
            referer="https://www.crunchyroll.com/videos/alphabetical",
        )


class Artist(EndpointFile[ArtistModel]):
    @override
    def _endpoint(self) -> ArtistEndpoint:
        return chirashi().artist

    # Occurs when a user puts in an invalid artist URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ArtistNotFoundError)


class ArtistMusicVideos(EndpointFile[ArtistMusicVideosModel]):
    @override
    def _endpoint(self) -> ArtistMusicVideosEndpoint:
        return chirashi().artist_music_videos


class ArtistConcerts(EndpointFile[ArtistConcertsModel]):
    @override
    def _endpoint(self) -> ArtistConcertsEndpoint:
        return chirashi().artist_concerts


class MusicVideo(EndpointFile[MusicVideoModel]):
    @override
    def _endpoint(self) -> MusicVideoEndpoint:
        return chirashi().music_video

    # Occurs when a user puts in an invalid music video URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MusicVideoNotFoundError)


class Concert(EndpointFile[ConcertModel]):
    @override
    def _endpoint(self) -> ConcertEndpoint:
        return chirashi().concert

    # Occurs when a user puts in an invalid concert URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ConcertNotFoundError)


class BrowseMusic(PagedEndpointFile[BrowseMusicModel]):
    @override
    def _endpoint(self) -> BrowseMusicEndpoint:
        return chirashi().browse_music

    @override
    def _download_pages(self) -> list[str]:
        return self._endpoint().download_all()

    def datums(self) -> list[BrowseMusicDatum]:
        return self._endpoint().extract_data(self.parsed())


class Search(EndpointFile[SearchModel]):
    @override
    def _endpoint(self) -> SearchEndpoint:
        return chirashi().search

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)
