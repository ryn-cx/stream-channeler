# TODO: Validate
"""Episode schemas."""

import uuid
from datetime import datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.episodes.models import BaseEpisode, Episode
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.seasons.models import Season


class EpisodeCreate(BaseCreateWithParentAndKey[Episode, Season], BaseEpisode):
    """Schema for creating an `Episode`."""


class EpisodeUpdate(
    make_model_with_all_fields_optional(BaseEpisode),
    BaseUpdateWithKey[Episode],
):
    """Schema for updating an `Episode`."""


class EpisodeOutput(BaseEpisode):
    """Schema for returning an `Episode`."""

    id: uuid.UUID
    season_id: uuid.UUID


# TODO: Consider reworking this into seperate models for each parent.
class EpisodeListOutput(EpisodeOutput):
    """Schema for returning a list of `Episode`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    username: str | None = Field(
        validation_alias=AliasPath(
            "season",
            "show",
            "source",
            "plugin",
            "user",
            "username",
        ),
    )
    season_name: str | None = Field(validation_alias=AliasPath("season", "name"))
    show_id: uuid.UUID = Field(validation_alias=AliasPath("season", "show_id"))
    show_name: str | None = Field(
        validation_alias=AliasPath("season", "show", "name"),
    )
    source_id: uuid.UUID = Field(
        validation_alias=AliasPath("season", "show", "source_id"),
    )
    source_name: str | None = Field(
        validation_alias=AliasPath("season", "show", "source", "name"),
    )
    plugin_id: uuid.UUID = Field(
        validation_alias=AliasPath("season", "show", "source", "plugin_id"),
    )
    plugin_name: str | None = Field(
        validation_alias=AliasPath("season", "show", "source", "plugin", "name"),
    )


class EpisodeInformationSide(BaseModel):
    """One record's own account of an episode, as the website that holds it has it."""

    label: str
    name: str | None
    description: str | None
    image_url: str | None
    duration: int | None
    release_date: datetime | None
    air_date: datetime | None
    episode_number: int | None
    season_number: int | None
    season_name: str | None
    show_name: str | None
    url: str | None
    key: str


class EpisodeInformationOutput(BaseModel):
    """What the website and TMDB each say about an episode, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    episode_id: uuid.UUID
    episode_identifier: str
    episode_identifier_locked: bool
    issue_report: str | None
    source: EpisodeInformationSide
    tmdb: EpisodeInformationSide | None


class EpisodeIssueReportInput(BaseModel):
    """Schema for reporting what is wrong with an `Episode`."""

    report: str = Field(min_length=1)


class EpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[EpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
