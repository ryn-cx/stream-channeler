# TODO: Validate
"""Season schemas."""

import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.schemas import BaseCreateWithParentAndKey, BaseUpdateWithKey
from app.seasons.models import BaseSeason, Season
from app.shows.models import Show


class SeasonCreate(BaseCreateWithParentAndKey[Season, Show], BaseSeason):
    """Schema for creating a `Season`."""


class SeasonUpdate(BaseUpdateWithKey[Season], BaseSeason):
    """Schema for updating a `Season`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment]


class SeasonOutput(BaseSeason):
    """Schema for returning a `Season`."""

    show_id: uuid.UUID
    id: uuid.UUID


class SeasonsPublic(BaseModel):
    """Schema for returning a list of `Season`s."""

    data: list[SeasonOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
