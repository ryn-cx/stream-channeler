# TODO: Validate
"""Show schemas."""

import uuid

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.shows.models import BaseShow, Show
from app.sources.models import Source


# TODO: Validate
class ShowCreate(BaseCreateWithParentAndKey[Show, Source], BaseShow):
    """Schema for creating a `Show`."""


# TODO: Validate
class ShowUpdate(
    make_model_with_all_fields_optional(BaseShow),
    BaseUpdateWithKey[Show],
):
    """Schema for updating a `Show`."""


# TODO: Validate
class ShowPublic(BaseShow):
    """Schema for returning a `Show`."""

    source_id: uuid.UUID
    id: uuid.UUID


# TODO: Consider reworking this into seperate models for each parent.
# TODO: Validate
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


# TODO: Validate
class ShowInformationSide(BaseModel):
    """One record's own account of a title, as the website that holds it has it."""

    label: str
    name: str | None
    media_type: str | None
    description: str | None
    image_url: str | None
    url: str | None
    key: str


# TODO: Validate
class ShowInformationOutput(BaseModel):
    """What the website and TMDB each say about a title, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    show_id: uuid.UUID
    show_identifier: str
    show_identifier_locked: bool
    editable: bool
    issue_reports: list[IssueReportOutput]
    source: ShowInformationSide
    tmdb: ShowInformationSide | None


# TODO: Validate
class ShowsPublic(BaseModel):
    """Schema for returning a list of `Show`s."""

    data: list[ShowListPublic]
    total_count: int
    filtered_count: int
    is_server_side: bool
