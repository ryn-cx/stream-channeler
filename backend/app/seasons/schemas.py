"""Season schemas."""

import uuid

from pydantic import AliasPath, BaseModel, ConfigDict, Field

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


# TODO: Consider reworking this into seperate models for each parent.
class SeasonListOutput(SeasonOutput):
    """Schema for returning a list of `Season`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    username: str | None = Field(
        validation_alias=AliasPath("show", "source", "plugin", "user", "username"),
    )
    show_name: str | None = Field(validation_alias=AliasPath("show", "name"))
    source_id: uuid.UUID = Field(validation_alias=AliasPath("show", "source_id"))
    source_name: str | None = Field(
        validation_alias=AliasPath("show", "source", "name"),
    )
    plugin_id: uuid.UUID = Field(
        validation_alias=AliasPath("show", "source", "plugin_id"),
    )
    plugin_name: str | None = Field(
        validation_alias=AliasPath("show", "source", "plugin", "name"),
    )


class SeasonsPublic(BaseModel):
    """Schema for returning a list of `Season`s."""

    data: list[SeasonListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
