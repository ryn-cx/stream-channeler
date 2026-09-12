# TODO: Validate
import json
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
from chirashi.categories import Categories as CategoriesEndpoint
from chirashi.categories.models import CategoriesModel
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
from chirashi.similar_to import SimilarTo as SimilarToEndpoint
from chirashi.similar_to.models import SimilarToModel
from get_around import GetAround

from app.config import settings
from app.utils import tz_datetime
from plugins.utils.base_plugin.files import (
    PagedEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.constants import INCOMPLETE_STATUS
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def chirashi() -> Chirashi:
    return Chirashi(get_around_client=get_around_client())


# TODO: Validate
class Series(SingleArgEndpointFile[SeriesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeriesEndpoint:
        return chirashi().series

    # Occurs when a user puts in an invalid series URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class Categories(SingleArgEndpointFile[CategoriesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> CategoriesEndpoint:
        return chirashi().categories

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class SimilarTo(SingleArgEndpointFile[SimilarToModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SimilarToEndpoint:
        return chirashi().similar_to


# TODO: Validate
class Objects(SingleArgEndpointFile[ObjectsModel]):
    """Episode information."""

    # TODO: Validate
    @override
    def _endpoint(self) -> ObjectsEndpoint:
        return chirashi().objects

    # Occurs when a user puts in an invalid episode URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, EpisodeNotFoundError)


# TODO: Validate
class Seasons(SingleArgEndpointFile[SeasonsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonsEndpoint:
        return chirashi().seasons


# TODO: Validate
class SeasonEpisodes(SingleArgEndpointFile[SeasonEpisodesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonEpisodesEndpoint:
        return chirashi().season_episodes


# TODO: Validate
class BaseBrowseSeries(PagedEndpointFile[BrowseSeriesModel], ABC):
    # TODO: Validate
    @override
    def _endpoint(self) -> BrowseSeriesEndpoint:  # type: ignore[override]
        return chirashi().browse_series

    # TODO: Validate
    def datums(self) -> list[BrowseSeriesDatum]:
        return self._endpoint().extract_data(self.parsed())


# TODO: Validate
class BrowseSeries(BaseBrowseSeries):
    # TODO: Validate
    @override
    def _initial_status_after_downloading(self) -> str:
        return INCOMPLETE_STATUS

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(
            self._endpoint().download_until_datetime(
                end_datetime=tz_datetime.fromisoformat(self.unique_identifier),
            ),
        )


# TODO: Validate
class Catalogue(BaseBrowseSeries):
    """Special BrowseSeries that contains all of the titles on Crunchyroll."""

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=7)

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(
            self._endpoint().download_until_datetime(
                end_datetime=datetime.min.replace(tzinfo=UTC),
                n=50,
                sort_by="alphabetical",
                referer="https://www.crunchyroll.com/videos/alphabetical",
            ),
        )


# TODO: Validate
class Artist(SingleArgEndpointFile[ArtistModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ArtistEndpoint:
        return chirashi().artist

    # Occurs when a user puts in an invalid artist URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ArtistNotFoundError)


# TODO: Validate
class ArtistMusicVideos(SingleArgEndpointFile[ArtistMusicVideosModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ArtistMusicVideosEndpoint:
        return chirashi().artist_music_videos


# TODO: Validate
class ArtistConcerts(SingleArgEndpointFile[ArtistConcertsModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ArtistConcertsEndpoint:
        return chirashi().artist_concerts


# TODO: Validate
class MusicVideo(SingleArgEndpointFile[MusicVideoModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> MusicVideoEndpoint:
        return chirashi().music_video

    # Occurs when a user puts in an invalid music video URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MusicVideoNotFoundError)


# TODO: Validate
class Concert(SingleArgEndpointFile[ConcertModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> ConcertEndpoint:
        return chirashi().concert

    # Occurs when a user puts in an invalid concert URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ConcertNotFoundError)


# TODO: Validate
class BrowseMusic(PagedEndpointFile[BrowseMusicModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> BrowseMusicEndpoint:  # type: ignore[override]
        return chirashi().browse_music

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(self._endpoint().download_all())

    # TODO: Validate
    def datums(self) -> list[BrowseMusicDatum]:
        return self._endpoint().extract_data(self.parsed())
