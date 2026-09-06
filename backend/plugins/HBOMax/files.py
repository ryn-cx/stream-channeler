# TODO: Validate
"""The files HBO Max is read out of."""

from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING, override

from minbo import MinBO
from minbo.exceptions import MovieNotFoundError, ShowNotFoundError
from minbo.movie import Movie as MovieEndpoint
from minbo.movie.models import MovieModel
from minbo.show import Show as TitleEndpoint
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
class TitleFile(EndpointFile[ShowModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> TitleEndpoint:
        return minbo().show

    # TODO: Validate
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
        title_id: str,
        season_number: int,
    ) -> None:
        self.title_id = title_id
        self.season_number = season_number
        super().__init__(session, plugin, f"{title_id}/{season_number}")

    # TODO: Validate
    @override
    def _endpoint(self) -> TitleEndpoint:
        return minbo().show

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.title_id, self.season_number)

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class MovieFile(EndpointFile[MovieModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> MovieEndpoint:
        return minbo().movie

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)
