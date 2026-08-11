# TODO: Validate
"""Season schemas."""

import uuid

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.seasons.models import BaseSeason, Season
from app.shows.models import Show


# TODO: Validate
class SeasonCreate(BaseCreateWithParentAndKey[Season, Show], BaseSeason):
    """Schema for creating a `Season`."""


# TODO: Validate
class SeasonUpdate(
    make_model_with_all_fields_optional(BaseSeason),
    BaseUpdateWithKey[Season],
):
    """Schema for updating a `Season`."""


# TODO: Validate
class SeasonOutput(BaseSeason):
    """Schema for returning a `Season`."""

    show_id: uuid.UUID
    id: uuid.UUID
    # The season this is a copy of, which is what the record is served as and
    # what a channel's season filter names.
    canonical_season_id: uuid.UUID
    # The TMDB season behind that, when TMDB has a record of it.
    tmdb_id: int | None = None
    # What the season is, said the same way wherever it turns up. Two rows
    # sharing it are the same season listed twice -- deliberately, so each
    # listing can be filtered on its own -- and this is what collapses them
    # when a normalised view is wanted.
    canonical_key: str | None = None


# TODO: Consider reworking this into seperate models for each parent.
# TODO: Validate
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


# TODO: Validate
class SeasonInformationSide(BaseModel):
    """One record's own account of a season, as the website that holds it has it."""

    label: str
    name: str | None
    season_number: int | None
    sort_order: int | None
    image_url: str | None
    show_name: str | None
    url: str | None
    key: str


# TODO: Validate
class SeasonInformationOutput(BaseModel):
    """What the website and TMDB each say about a season, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    season_id: uuid.UUID
    issue_reports: list[IssueReportOutput]
    source: SeasonInformationSide
    tmdb: SeasonInformationSide | None


# TODO: Validate
class SeasonsPublic(BaseModel):
    """Schema for returning a list of `Season`s."""

    data: list[SeasonListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
