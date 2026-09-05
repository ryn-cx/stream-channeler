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
from trivial_minus.show import Show as ShowEndpoint
from trivial_minus.show.models import ShowModel

from plugins.utils.base_plugin_v3.files import EndpointFile
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def trivial_minus() -> TrivialMinus:
    return TrivialMinus(get_around_client=get_around_client())


# TODO: Validate
class ShowPage(EndpointFile[ShowModel]):
    @override
    def _endpoint(self) -> ShowEndpoint:
        return trivial_minus().show

    @classmethod
    @override
    def _identifier_suffix(cls) -> str:
        return ".html"

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)

    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid show {self.unique_identifier}"


# TODO: Validate
class EpisodesFile(EndpointFile[EpisodesModel]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        show_id: str,
        season_number: int,
    ) -> None:
        self.show_id = show_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{show_id}/{season_number}")

    @override
    def _endpoint(self) -> EpisodesEndpoint:
        return trivial_minus().episodes

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            self.show_id,
            season_number=self.season_number,
        )


# TODO: Validate
class MovieFile(EndpointFile[MovieModel]):
    @override
    def _endpoint(self) -> MovieEndpoint:
        return trivial_minus().movie

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)

    @override
    def acceptable_error_status(self) -> str:
        return f"Invalid movie_id {self.unique_identifier}"
