# TODO: Validate
"""The files HBO Max is read out of."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, override

from minbo import MinBO
from minbo.exceptions import MovieNotFoundError, ShowNotFoundError
from minbo.movie import Movie as MovieEndpoint
from minbo.movie.models import MovieModel
from minbo.show import Show as ShowEndpoint
from minbo.show.models import ShowModel

from plugins.utils.base_plugin.files import EndpointFile
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def minbo() -> MinBO:
    return MinBO(get_around_client=get_around_client())


# TODO: Validate
class ShowFile(EndpointFile[ShowModel]):
    @override
    def _endpoint(self) -> ShowEndpoint:
        return minbo().show

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class SeasonFile(EndpointFile[ShowModel]):
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
    def _endpoint(self) -> ShowEndpoint:
        return minbo().show

    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.show_id, self.season_number)

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class MovieFile(EndpointFile[MovieModel]):
    @override
    def _endpoint(self) -> MovieEndpoint:
        return minbo().movie

    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)
