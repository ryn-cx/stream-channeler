"""Show schemas."""

import uuid

from pydantic import AliasPath, BaseModel, ConfigDict, Field

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


# TODO: Consider reworking this into seperate models for each parent.
class ShowListPublic(ShowPublic):
    """Schema for returning a list of `Show`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    username: str | None = Field(
        validation_alias=AliasPath("source", "plugin", "user", "username"),
    )
    source_name: str | None = Field(validation_alias=AliasPath("source", "name"))
    plugin_id: uuid.UUID = Field(validation_alias=AliasPath("source", "plugin_id"))
    plugin_name: str | None = Field(
        validation_alias=AliasPath("source", "plugin", "name"),
    )


class ShowsPublic(BaseModel):
    """Schema for returning a list of `Show`s."""

    data: list[ShowListPublic]
    total_count: int
    filtered_count: int
    is_server_side: bool
