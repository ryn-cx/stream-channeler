# TODO: Validate
"""The files Hulu is read out of."""

from collections.abc import Sequence
from functools import cache
from http import HTTPStatus
from typing import Any, override

from sqlmodel import Session
from wholoo import Wholoo
from wholoo.episode import Episode as EpisodeEndpoint
from wholoo.episode.models import EpisodeModel
from wholoo.exceptions import (
    EpisodeNotFoundError,
    HTTPError,
    MovieNotFoundError,
    SeriesNotFoundError,
)
from wholoo.genre import Genre as GenreEndpoint
from wholoo.genre.models import GenreModel
from wholoo.genres import Genres as GenresEndpoint
from wholoo.genres.models import GenresModel
from wholoo.movies import Movies as MoviesEndpoint
from wholoo.movies.models import MoviesModel
from wholoo.season import Season as SeasonEndpoint
from wholoo.season.models import SeasonModel
from wholoo.tv import TV
from wholoo.tv.models import TVModel

from app.plugins.models import Plugin
from plugins.Hulu.utils import UtilsMixin, listed_items, season_numbers
from plugins.utils.base_plugin_v2.files import BaseFile, EndpointFile, TextFile
from plugins.utils.get_around_client import get_around_client


@cache
def wholoo() -> Wholoo:
    return Wholoo(get_around_client=get_around_client())


# TODO: Update the model name in wholoo to match this.
class _Series(EndpointFile[TVModel]):
    @override
    def _endpoint(self) -> TV:
        return wholoo().tv

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, SeriesNotFoundError)


class _Movie(EndpointFile[MoviesModel]):
    @override
    def _endpoint(self) -> MoviesEndpoint:
        return wholoo().movies

    # Occurs if the user tries to add an invalid URL.
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


class _Season(EndpointFile[SeasonModel]):
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


class _Episode(EndpointFile[EpisodeModel]):
    @override
    def _endpoint(self) -> EpisodeEndpoint:
        return wholoo().episode

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        if isinstance(error, EpisodeNotFoundError):
            return True
        return (
            isinstance(error, HTTPError) and error.status_code == HTTPStatus.BAD_REQUEST
        )


class _Genres(EndpointFile[GenresModel]):
    @override
    def _endpoint(self) -> GenresEndpoint:
        return wholoo().genres

    @override
    def _download_file(self) -> str:
        return self._endpoint().download()


class _Genre(EndpointFile[GenreModel]):
    @override
    def _endpoint(self) -> GenreEndpoint:
        return wholoo().genre


# TODO: Validate
class _WatchRedirect(TextFile):
    """Where a watch link points.

    A watch link is keyed by an episode id and is answered by pointing at the
    series or the movie the episode belongs to. Which of the two it points at
    says which importer reads the link, without the episode being downloaded.
    """

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, episode_key: str) -> None:
        self.episode_key = episode_key
        self.unique_identifier = episode_key
        super().__init__(session, plugin)

    # TODO: Validate
    @override
    def _download(self) -> None:
        with self._log_download(self.episode_key):
            response = get_around_client().get(
                UtilsMixin.build_url(f"watch/{self.episode_key}"),
                follow_redirects=False,
            )
            self.write(response.headers.get("location"))

    # TODO: Validate
    def location(self) -> str | None:
        return self.database_record.content


# TODO: Validate
class FileMixin(UtilsMixin):
    # TODO: Validate
    def watch_redirect_file(self, episode_key: str) -> _WatchRedirect:
        return self._file(_WatchRedirect, episode_key)

    def genres_file(self) -> _Genres:
        return self._file(_Genres, "genres")

    def genre_file(self, genre_id: str) -> _Genre:
        return self._file(_Genre, genre_id)

    def series_file(self, series_id: str) -> _Series:
        return self._file(_Series, series_id)

    def episode_file(self, episode_id: str) -> _Episode:
        return self._file(_Episode, episode_id)

    def movie_file(self, movie_id: str) -> _Movie:
        return self._file(_Movie, movie_id)

    def season_file(self, series_id: str, season_number: int) -> _Season:
        return self._file(_Season, series_id, season_number)

    @override
    def _source_files(self) -> Sequence[BaseFile[Any]]:
        genres_page = self.genres_file()
        return [
            genres_page,
            *(
                self.genre_file(href.rsplit("/", 1)[-1])
                for _name, href in listed_items(genres_page.parsed())
            ),
        ]


# TODO: Validate
class SeriesFileMixin(FileMixin):
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        # Includes show information and the list of seasons.
        return [self.series_file(show_key)]

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        _, season_number = self._split_season_key(season_key)
        # Includes season information and the list of episodes.
        return [self.season_file(show_key, season_number)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        _, season_number = self._split_season_key(season_key)
        # Includes episode information.
        return [self.season_file(show_key, season_number)]

    # TODO: Validate
    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [
            self._season_key(show_key, season_number)
            for season_number in season_numbers(self.series_file(show_key).parsed())
        ]

    # TODO: Validate
    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        episode_keys: list[str] = []
        for season_key in season_keys:
            show_key, season_number = self._split_season_key(season_key)
            episode_keys += [
                str(item.id)
                for item in self.season_file(show_key, season_number).parsed().items
            ]
        return episode_keys


# TODO: Validate
class MovieFileMixin(FileMixin):
    @override
    def _show_files(self, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _season_files(self, season_key: str, show_key: str) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _episode_files(
        self,
        episode_key: str,
        season_key: str,
        show_key: str,
    ) -> Sequence[BaseFile[Any]]:
        return [self.movie_file(show_key)]

    @override
    def _season_keys_from_show_files(self, show_key: str) -> list[str]:
        return [self._season_key(show_key, 0)]

    @override
    def _episode_keys_from_season_files(
        self,
        season_keys: str | list[str],
        show_key: str,
    ) -> list[str]:
        if isinstance(season_keys, str):
            season_keys = [season_keys]
        return [self._split_season_key(season_key)[0] for season_key in season_keys]
