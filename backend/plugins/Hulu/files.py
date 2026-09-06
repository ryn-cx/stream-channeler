from datetime import datetime, timedelta
from functools import cache
from http import HTTPStatus
from typing import override

from bs4 import BeautifulSoup
from get_around import GetAround
from sqlmodel import Session
from wholoo import Wholoo
from wholoo.all_movies import AllMovies as AllMoviesEndpoint
from wholoo.all_movies.models import AllMoviesModel
from wholoo.all_series import AllSeries as AllSeriesEndpoint
from wholoo.all_series.models import AllSeriesModel
from wholoo.episode import Episode as EpisodeEndpoint
from wholoo.episode.models import EpisodeModel
from wholoo.exceptions import (
    EpisodeNotFoundError,
    HTTPError,
    MovieNotFoundError,
    SeriesNotFoundError,
)
from wholoo.movies import Movies as MoviesEndpoint
from wholoo.movies.models import MoviesModel
from wholoo.search import Search as SearchEndpoint
from wholoo.search.models import SearchModel
from wholoo.season import Season as SeasonEndpoint
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import TVModel

from app.config import settings
from app.plugins.models import Plugin
from app.utils import tz_datetime
from plugins.Hulu.utils import episode_url
from plugins.utils.base_plugin.files import EndpointFile, TextFile


# TODO: This is a temporary importing workaround.
# from plugins.utils.get_around_client import get_around_client
@cache
def get_around_client() -> GetAround:
    return GetAround(proxy=settings.PROXY)


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client())


# TODO: Update the model name in wholoo to match this.
class Series(EndpointFile[TVModel]):
    @override
    def _endpoint(self) -> TV:
        return wholoo().tv

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


class Movie(EndpointFile[MoviesModel]):
    @override
    def _endpoint(self) -> MoviesEndpoint:
        return wholoo().movies

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


class Season(EndpointFile[SeasonModel]):
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return wholoo().season

    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        series_id: str,
        season_number: int,
    ) -> None:
        self.series_id = series_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{series_id}/{season_number}")

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.series_id, self.season_number)


class Episode(EndpointFile[EpisodeModel]):
    @override
    def _endpoint(self) -> EpisodeEndpoint:
        return wholoo().episode


class Search(EndpointFile[SearchModel]):
    @override
    def _endpoint(self) -> SearchEndpoint:
        return wholoo().search

    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + timedelta(days=30)


class AllSeries(EndpointFile[AllSeriesModel]):
    @override
    def _endpoint(self) -> AllSeriesEndpoint:
        return wholoo().all_series

    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


class AllMovies(EndpointFile[AllMoviesModel]):
    @override
    def _endpoint(self) -> AllMoviesEndpoint:
        return wholoo().all_movies

    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


class WatchRedirect(TextFile):
    @override
    def _download(self) -> None:
        with self._log_download(self.unique_identifier):
            response = get_around_client().get(
                episode_url(self.unique_identifier),
                follow_redirects=True,
            )
            response.raise_for_status()
            canonical = BeautifulSoup(response.text, "html.parser").select_one(
                'link[rel="canonical"]',
            )
            if canonical is None:
                msg = f"No canonical URL for {episode_url(self.unique_identifier)}"
                raise ValueError(msg)
            self.write(str(canonical["href"]))
