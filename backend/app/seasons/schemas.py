"""Season schemas."""

import uuid

from pydantic import BaseModel

from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.seasons.models import BaseSeason, Season
from app.shows.models import Show


class SeasonCreate(BaseCreateWithParentAndKey[Season, Show], BaseSeason):
    """Schema for creating a `Season`."""


class SeasonUpdate(
    make_model_with_all_fields_optional(BaseSeason),
    BaseUpdateWithKey[Season],
):
    """Schema for updating a `Season`."""


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
