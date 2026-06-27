"""Show schemas."""

import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.schemas import BaseCreateWithParentAndKey, BaseUpdateWithKey
from app.shows.models import BaseShow, Show
from app.sources.models import Source


class ShowCreate(BaseCreateWithParentAndKey[Show, Source], BaseShow):
    """Schema for creating a `Show`."""


class ShowUpdate(BaseUpdateWithKey[Show], BaseShow):
    """Schema for updating a `Show`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment]


class ShowPublic(BaseShow):
    """Schema for returning a `Show`."""

    source_id: uuid.UUID
    id: uuid.UUID


class ShowTableOutput(BaseModel):
    """Schema for returning a list of `Show`s."""

    data: list[ShowPublic]
    count: int
    server_side: bool
