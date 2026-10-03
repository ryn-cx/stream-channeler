# TODO: Validate
"""The files a Peacock title is read out of."""

from __future__ import annotations

from datetime import datetime
from functools import cache
from typing import TYPE_CHECKING, override

from pigeon import Pigeon
from pigeon.collection import Collection as CollectionEndpoint
from pigeon.collection.models import CollectionModel
from pigeon.exceptions import MovieNotFoundError, ShowNotFoundError
from pigeon.movie import Movie as MovieEndpoint
from pigeon.movie.models import MovieModel
from pigeon.show import Show as ShowEndpoint
from pigeon.show.models import ShowModel

from app.utils import tz_datetime
from plugins.utils.base_plugin.files import (
    MultipleArgEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.constants import COMPLETE_CATALOG_UPDATE_INTERVAL
from plugins.utils.proxy_client import proxy_client

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def pigeon() -> Pigeon:
    return Pigeon(get_around_client=proxy_client())


# TODO: Validate
class ShowFile(SingleArgEndpointFile[ShowModel]):
    """Contains all of a series' data (the series, its seasons and its episodes)."""

    # TODO: Validate
    @override
    def _endpoint(self) -> ShowEndpoint:
        return pigeon().show

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, ShowNotFoundError)


# TODO: Validate
class MovieFile(SingleArgEndpointFile[MovieModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> MovieEndpoint:
        return pigeon().movie

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, MovieNotFoundError)


# TODO: Validate
class CollectionFile(MultipleArgEndpointFile[CollectionModel]):
    """One of the A-Z listings the whole catalogue is read out of."""

    # TODO: Validate
    def __init__(self, session: Session, plugin: Plugin, slug: str) -> None:
        self.slug = slug
        super().__init__(session, plugin, slug.strip("/"))

    # TODO: Validate
    @override
    def _endpoint(self) -> CollectionEndpoint:
        return pigeon().collection

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(self.slug)

    # TODO: Validate
    @override
    def _next_update_at(self) -> datetime:
        return tz_datetime.now() + COMPLETE_CATALOG_UPDATE_INTERVAL
