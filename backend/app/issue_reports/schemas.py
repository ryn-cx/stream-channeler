# TODO: Validate
"""Issue report schemas."""

import uuid
from datetime import datetime
from enum import StrEnum

from pydantic import AliasPath, BaseModel, ConfigDict, Field


# TODO: Validate
class IssueReportMediaType(StrEnum):
    """Which kind of record a report was left on."""

    episode = "episode"
    season = "season"
    show = "show"


# TODO: Validate
class IssueReportCreate(BaseModel):
    """Schema for leaving an `IssueReport` on a record."""

    report: str = Field(min_length=1)


# TODO: Validate
class IssueReportUpdate(BaseModel):
    """Schema for rewriting an `IssueReport`."""

    report: str = Field(min_length=1)


# TODO: Validate
class IssueReportOutput(BaseModel):
    """Schema for returning an `IssueReport`.

    `user_id` and `username` are unset for a report left by a visitor with no
    account.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    id: uuid.UUID
    report: str
    created_at: datetime
    modified_at: datetime
    user_id: uuid.UUID | None
    username: str | None = Field(validation_alias=AliasPath("user", "username"))


# TODO: Validate
class IssueReportListOutput(IssueReportOutput):
    """Schema for returning an `IssueReport` alongside the record it was left on."""

    media_type: IssueReportMediaType
    media_id: uuid.UUID
    media_name: str | None
    season_name: str | None
    show_name: str | None
    source_name: str | None


# TODO: Validate
class IssueReportsListOutput(BaseModel):
    """Schema for returning every `IssueReport` on the site."""

    data: list[IssueReportListOutput]
