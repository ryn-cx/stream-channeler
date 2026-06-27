"""Source schemas."""

import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.plugins.models import Plugin
from app.schemas import BaseCreateWithParentAndKey, BaseUpdateWithKey
from app.sources.models import BaseSource, Source


class SourceCreate(BaseCreateWithParentAndKey[Source, Plugin], BaseSource):
    """Schema for creating a `Source`."""


class SourceUpdate(BaseUpdateWithKey[Source], BaseSource):
    """Schema for updating a `Source`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment]


class SourcePublic(BaseSource):
    """Schema for returning a `Source`."""

    plugin_id: uuid.UUID
    id: uuid.UUID


class SourceTableOutput(BaseModel):
    """Schema for returning a list of `Source`s."""

    data: list[SourcePublic]
    count: int
    server_side: bool
