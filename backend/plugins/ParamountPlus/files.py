# TODO: Validate
"""The files Paramount+ is read out of."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, override

from trivial_minus import TrivialMinus
from trivial_minus.episodes import Episodes as EpisodesEndpoint
from trivial_minus.episodes.models import EpisodesModel
from trivial_minus.exceptions import MovieNotFoundError, ShowNotFoundError
from trivial_minus.movie import Movie as MovieEndpoint
from trivial_minus.movie.models import MovieModel
from trivial_minus.show import Show as TitleEndpoint
from trivial_minus.show.models import ShowModel

from plugins.utils.base_plugin.files import SingleArgEndpointFile, MultipleArgEndpointFile
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def trivial_minus() -> TrivialMinus:
    return TrivialMinus(get_around_client=get_around_client())


# TODO: Validate
class TitlePage(SingleArgEndpointFile[ShowModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> TitleEndpoint:
        return trivial_minus().show

    # TODO: Validate
    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".html"

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid title {self.unique_identifier}"


# TODO: Validate
class EpisodesFile(MultipleArgEndpointFile[EpisodesModel]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        title_id: str,
        season_number: int,
    ) -> None:
        self.title_id = title_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{title_id}/{season_number}")

    # TODO: Validate
    @override
    def _endpoint(self) -> EpisodesEndpoint:
        return trivial_minus().episodes

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.title_id,
            season_number=self.season_number,
        )


# TODO: Validate
class MovieFile(SingleArgEndpointFile[MovieModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> MovieEndpoint:
        return trivial_minus().movie

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)

    # TODO: Validate
    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid movie_id {self.unique_identifier}"
