"""Source schemas."""

import uuid

from pydantic import AliasPath, BaseModel, ConfigDict, Field

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


# TODO: Consider reworking this into seperate models for each parent.
class SourceListPublic(SourcePublic):
    """Schema for returning a list of `Source`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    username: str | None = Field(
        validation_alias=AliasPath("plugin", "user", "username"),
    )
    plugin_name: str | None = Field(validation_alias=AliasPath("plugin", "name"))


class SourcesPublic(BaseModel):
    """Schema for returning a list of `Source`s."""

    data: list[SourceListPublic]
    total_count: int
    filtered_count: int
    is_server_side: bool
