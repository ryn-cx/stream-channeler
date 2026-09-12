# TODO: Validate
from functools import cache
from typing import override

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
    MovieNotFoundError,
    SeriesNotFoundError,
)
from wholoo.genre import Genre as GenreEndpoint
from wholoo.genre.models import GenreModel
from wholoo.genres import Genres as GenresEndpoint
from wholoo.genres.models import GenresModel
from wholoo.movies import Movies as MoviesEndpoint
from wholoo.movies.models import Component as MovieComponent
from wholoo.movies.models import Details as MovieDetails
from wholoo.movies.models import MoviesModel
from wholoo.search import Search as SearchEndpoint
from wholoo.search.models import SearchModel
from wholoo.season import Season as SeasonEndpoint
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import Component as SeriesComponent
from wholoo.tv.models import Details as TVDetails
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from plugins.utils.base_plugin.files import (
    MultipleArgEndpointFile,
    NoArgsEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client(proxy=True))


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
    def details(self) -> TVDetails:
        return self.parsed().details

    # TODO: Validate
    def components(self) -> list[SeriesComponent]:
        return self.parsed().components


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
    def details(self) -> MovieDetails:
        return self.parsed().details

    # TODO: Validate
    def components(self) -> list[MovieComponent]:
        return self.parsed().components


# TODO: Validate
class Episode(SingleArgEndpointFile[EpisodeModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> EpisodeEndpoint:
        return wholoo().episode

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, EpisodeNotFoundError)

    # TODO: Validate
    def series_key(self) -> str:
        return str(self.parsed().entity.series_id)


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
