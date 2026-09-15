# TODO: Validate
"""The files a Disney+ title is read out of."""

from __future__ import annotations

from functools import cache
from typing import override
from uuid import UUID

from kneeminus import KneeMinus
from kneeminus.entity import Entity as EntityEndpoint
from kneeminus.entity.models import EntityModel
from kneeminus.exceptions import EntityNotFoundError
from sqlmodel import Session

from app.plugins.models import Plugin
from plugins.utils.base_plugin.files import MultipleArgEndpointFile
from plugins.utils.get_around_client import get_around_client


# TODO: Validate
@cache
def kneeminus() -> KneeMinus:
    return KneeMinus(get_around_client=get_around_client())


# TODO: Validate
class Entity(MultipleArgEndpointFile[EntityModel]):
    # TODO: Validate
    @override
    def _endpoint(self) -> EntityEndpoint:
        return kneeminus().entity

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(UUID(self.unique_identifier))

    # Occurs when importing an invalid entity URL.
    # TODO: Validate
    @override
    def _is_acceptable_error(self, error: Exception) -> bool:
        return isinstance(error, EntityNotFoundError)


# TODO: Validate
class SeasonEntity(MultipleArgEndpointFile[EntityModel]):
    # TODO: Validate
    def __init__(
        self,
        session: Session,
        plugin: Plugin,
        entity_id: str,
        season_id: str,
    ) -> None:
        self.entity_id = entity_id
        self.season_id = season_id
        super().__init__(session, plugin, f"{entity_id}/{season_id}")

    # TODO: Validate
    @override
    def _endpoint(self) -> EntityEndpoint:
        return kneeminus().entity

    # TODO: Validate
    @override
    def _download_file(self) -> str:
        return self._endpoint().download(
            UUID(self.entity_id),
            season_id=UUID(self.season_id),
        )
