# TODO: Validate
from functools import cache
from typing import override

from bs4 import BeautifulSoup
from sqlmodel import Session
from wholoo import Wholoo
from wholoo.all_movies import AllMovies as AllMoviesEndpoint
from wholoo.all_movies.models import AllMoviesModel
from wholoo.all_series import AllSeries as AllSeriesEndpoint
from wholoo.all_series.models import AllSeriesModel
from wholoo.episode import Episode as EpisodeEndpoint
from wholoo.episode.models import EpisodeModel
from wholoo.exceptions import (
    MovieNotFoundError,
    SeriesNotFoundError,
)
from wholoo.genre import Genre as GenreEndpoint
from wholoo.genre.models import GenreModel
from wholoo.genres import Genres as GenresEndpoint
from wholoo.genres.models import GenresModel
from wholoo.movies import Movies as MoviesEndpoint
from wholoo.movies.models import MoviesModel
from wholoo.search import Search as SearchEndpoint
from wholoo.search.models import SearchModel
from wholoo.season import Season as SeasonEndpoint
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from plugins.Hulu.utils import episode_url
from plugins.utils.base_plugin.files import (
    SingleArgEndpointFile,
    MultipleArgEndpointFile,
    NoArgsEndpointFile,
    TextFile,
)
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client())


# TODO: Update the model name in wholoo to match this.
# TODO: Validate
class Series(SingleArgEndpointFile[TVModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> TV:
        return wholoo().tv

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


# TODO: Validate
class Movie(SingleArgEndpointFile[MoviesModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> MoviesEndpoint:
        return wholoo().movies

    # Occurs if the user tries to add an invalid URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


# TODO: Validate
class Season(MultipleArgEndpointFile[SeasonModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> SeasonEndpoint:
        return wholoo().season

    # TODO: Validate
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

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.series_id, self.season_number)


class Episode(SingleArgEndpointFile[EpisodeModel]):
    @override
    def _endpoint(self) -> EpisodeEndpoint:
        return wholoo().episode


class Search(SingleArgEndpointFile[SearchModel]):
    @override
    def _endpoint(self) -> SearchEndpoint:
        return wholoo().search


class AllSeries(NoArgsEndpointFile[AllSeriesModel]):
    unique_identifier = "all_series"

    @override
    def _endpoint(self) -> AllSeriesEndpoint:
        return wholoo().all_series


class AllMovies(NoArgsEndpointFile[AllMoviesModel]):
    unique_identifier = "all_movies"

    @override
    def _endpoint(self) -> AllMoviesEndpoint:
        return wholoo().all_movies


class Genres(NoArgsEndpointFile[GenresModel]):
    unique_identifier = "genres"

    @override
    def _endpoint(self) -> GenresEndpoint:
        return wholoo().genres


class Genre(SingleArgEndpointFile[GenreModel]):
    @override
    def _endpoint(self) -> GenreEndpoint:
        return wholoo().genre


# TODO: Validate
class WatchRedirect(TextFile):
    # TODO: Validate
    @override
    def _download_file(self) -> str:
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
        return str(canonical["href"])
