"""Source schemas."""

import uuid

from pydantic import BaseModel

from app.plugins.models import Plugin
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.sources.models import BaseSource, Source


class SourceCreate(BaseCreateWithParentAndKey[Source, Plugin], BaseSource):
    """Schema for creating a `Source`."""


class SourceUpdate(
    make_model_with_all_fields_optional(BaseSource),
    BaseUpdateWithKey[Source],
):
    """Schema for updating a `Source`."""


class SourcePublic(BaseSource):
    """Schema for returning a `Source`."""

    plugin_id: uuid.UUID
    id: uuid.UUID


class SourcesPublic(BaseModel):
    """Schema for returning a list of `Source`s."""

    data: list[SourcePublic]
    total_count: int
    filtered_count: int
    is_server_side: bool
