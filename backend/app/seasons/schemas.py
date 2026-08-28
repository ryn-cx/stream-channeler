# TODO: Validate
"""Season schemas."""

import uuid
from typing import Self

from pydantic import AliasPath, BaseModel, ConfigDict, Field, model_validator

from app.canonical_media.metadata import tmdb_season_url
from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.seasons.models import BaseSeason, Season
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourceListPublic


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
    # The season's own page on themoviedb.org. TMDB builds the address out of the
    # key of the title above the season rather than out of anything the season
    # carries, so it is filled in where the title is at hand and left empty here.
    tmdb_url: str | None = None


# TODO: Consider reworking this into seperate models for each parent.
# TODO: Validate
class SeasonListOutput(SeasonOutput):
    """Schema for returning a list of `Season`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

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
class SeasonRecord(BaseModel):
    """A `Season` and what holds it, each served as the record it already is."""

    season: SeasonOutput
    show: ShowPublic
    source: SourceListPublic

    # TODO: Validate
    @model_validator(mode="after")
    def _read_tmdb_url(self) -> Self:
        self.season.tmdb_url = tmdb_season_url(
            self.show.key,
            self.season.season_number,
        )
        return self


# TODO: Validate
class SeasonInformationSide(SeasonRecord):
    """One record's own account of a season, as the website that holds it has it."""

    label: str


# TODO: Validate
class SeasonInformationOutput(BaseModel):
    """What the website and TMDB each say about a season, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

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
