# TODO: Validate
"""The files Paramount+ is read out of."""

from __future__ import annotations

import json
from functools import cache
from typing import TYPE_CHECKING, override

from trivial_minus import TrivialMinus
from trivial_minus.carousel import Carousel as CarouselEndpoint
from trivial_minus.carousel.models import CarouselModel
from trivial_minus.carousel.models import Datum as CarouselDatum
from trivial_minus.collection import Collection as CollectionEndpoint
from trivial_minus.collection.models import CollectionModel
from trivial_minus.collections import Collections as CollectionsEndpoint
from trivial_minus.collections.models import CollectionsModel
from trivial_minus.episodes import Episodes as EpisodesEndpoint
from trivial_minus.episodes.models import EpisodesModel
from trivial_minus.exceptions import (
    CollectionNotFoundError,
    MovieNotFoundError,
    ShowNotFoundError,
)
from trivial_minus.movie import Movie as MovieEndpoint
from trivial_minus.movie.models import MovieModel
from trivial_minus.section import Section as SectionEndpoint
from trivial_minus.section.models import SectionModel
from trivial_minus.show import Show as TitleEndpoint
from trivial_minus.show.models import ShowModel

from plugins.utils.base_plugin.files import (
    APIClientFile,
    MultipleArgEndpointFile,
    NoArgsEndpointFile,
    SingleArgEndpointFile,
)
from plugins.utils.get_around_client import get_around_client

if TYPE_CHECKING:
    from sqlmodel import Session

    from app.plugins.models import Plugin


# TODO: Validate
@cache
def trivial_minus() -> TrivialMinus:
    return TrivialMinus(get_around_client=get_around_client())


# TODO: Validate
def carousel_entries(carousel: CarouselModel) -> list[CarouselDatum]:
    if isinstance(carousel.data, list):
        return carousel.data
    return []


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
class SectionFile(APIClientFile[list[SectionModel]]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        title_id: str,
        section_id: int,
    ) -> None:
        self.title_id = title_id
        self.section_id = section_id
        super().__init__(session, plugin, f"{title_id}/{section_id}")

    # TODO: Validate
    @override
    def _endpoint(self) -> SectionEndpoint:
        return trivial_minus().section

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(
            self._endpoint().download_all(
                self.title_id,
                section_id=self.section_id,
            ),
        )

    # TODO: Validate
    @override
    def _parse(self, content: str) -> list[SectionModel]:
        pages: list[str] = json.loads(content)
        return [self._endpoint().load(page, self.log_id()) for page in pages]


# TODO: Validate
class CollectionsFile(NoArgsEndpointFile[CollectionsModel]):
    unique_identifier = "Collections"

    # TODO: Validate
    @override
    def _endpoint(self) -> CollectionsEndpoint:
        return trivial_minus().collections


# TODO: Validate
class CollectionFile(SingleArgEndpointFile[CollectionModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> CollectionEndpoint:
        return trivial_minus().collection

    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, CollectionNotFoundError)


# TODO: Validate
class CarouselFile(APIClientFile[list[CarouselModel]]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        collection_id: str,
        carousel_id: str,
        token: str,
    ) -> None:
        self.collection_id = collection_id
        self.carousel_id = carousel_id
        self.token = token
        super().__init__(session, plugin, f"{collection_id}/{carousel_id}")

    # TODO: Validate
    @override
    def _endpoint(self) -> CarouselEndpoint:
        return trivial_minus().carousel

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return json.dumps(
            self._endpoint().download_all(self.collection_id, token=self.token),
        )

    # TODO: Validate
    @override
    def _parse(self, content: str) -> list[CarouselModel]:
        pages: list[str] = json.loads(content)
        return [self._endpoint().load(page, self.log_id()) for page in pages]


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
