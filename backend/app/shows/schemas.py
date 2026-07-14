"""Show schemas."""

import uuid

from pydantic import BaseModel

from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.shows.models import BaseShow, Show
from app.sources.models import Source


class ShowCreate(BaseCreateWithParentAndKey[Show, Source], BaseShow):
    """Schema for creating a `Show`."""


class ShowUpdate(
    make_model_with_all_fields_optional(BaseShow),
    BaseUpdateWithKey[Show],
):
    """Schema for updating a `Show`."""


class ShowPublic(BaseShow):
    """Schema for returning a `Show`."""

    source_id: uuid.UUID
    id: uuid.UUID


class ShowsPublic(BaseModel):
    """Schema for returning a list of `Show`s."""

    data: list[ShowPublic]
    total_count: int
    filtered_count: int
    is_server_side: bool
