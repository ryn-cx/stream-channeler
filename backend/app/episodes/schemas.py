# TODO: Validate
"""Episode schemas."""

import uuid
from datetime import datetime
from typing import Self

from pydantic import AliasPath, BaseModel, ConfigDict, Field, model_validator

from app.canonical_media.keys import EPISODE_LEVEL, tmdb_id_of
from app.episodes.models import BaseCanonicalEpisode, BaseEpisode, Episode
from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.seasons.models import Season


# TODO: Validate
class EpisodeCreate(BaseCreateWithParentAndKey[Episode, Season], BaseEpisode):
    """Schema for creating an `Episode`."""


# TODO: Validate
class EpisodeUpdate(
    make_model_with_all_fields_optional(BaseEpisode),
    BaseUpdateWithKey[Episode],
):
    """Schema for updating an `Episode`."""


# TODO: Validate
class EpisodeOutput(BaseEpisode):
    """Schema for returning an `Episode`."""

    id: uuid.UUID
    season_id: uuid.UUID
    # The episode this is a copy of, which is what the record is served as and
    # what a watch, a channel filter and a saved position all name.
    canonical_episode_id: uuid.UUID
    # The TMDB episode behind that, when TMDB has a record of it.
    tmdb_id: int | None = None
    # What the episode is, said the same way wherever it turns up. Two rows
    # sharing it are the same episode listed twice -- deliberately, so each
    # listing can be filtered on its own -- and this is what collapses them
    # when a normalised view is wanted.
    canonical_key: str | None = None


# TODO: Consider reworking this into seperate models for each parent.
# TODO: Validate
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


# TODO: Validate
class EpisodeInformationSide(BaseModel):
    """One record's own account of an episode, as the website that holds it has it."""

    label: str
    name: str | None
    description: str | None
    image_url: str | None
    duration: int | None
    air_date: datetime | None
    episode_number: int | None
    sort_order: int | None
    season_number: int | None
    season_name: str | None
    show_name: str | None
    url: str | None
    key: str
    canonical_episode_locked: bool
    canonical_episode_note: str | None
    data_timestamp: datetime | None
    update_at: datetime | None
    modified_at: datetime | None


# TODO: Validate
class EpisodeInformationOutput(BaseModel):
    """What the website and TMDB each say about an episode, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    episode_id: uuid.UUID
    canonical_episode_locked: bool
    canonical_episode_note: str | None
    issue_reports: list[IssueReportOutput]
    source: EpisodeInformationSide
    tmdb: EpisodeInformationSide | None


# TODO: Validate
class EpisodeUsingTmdb(BaseModel):
    """One of the show's episodes that already points at a TMDB episode."""

    id: uuid.UUID
    name: str | None
    season_number: int | None
    episode_number: int | None
    url: str | None


# TODO: Validate
class TmdbEpisodeChoice(BaseModel):
    """A TMDB episode, as one of the episodes an `Episode` can be linked to."""

    canonical_episode_id: uuid.UUID
    # The rows themselves, so the match can be opened on its own page here the
    # same way the episode beside it can. TMDB's records are canonical rows, so
    # these are the ids of the very rows, not of copies of them.
    season_id: uuid.UUID
    show_id: uuid.UUID
    tmdb_episode_id: int
    name: str
    show_name: str
    show_year: int | None
    source_name: str | None
    plugin_name: str | None
    season_number: int
    episode_number: int
    absolute_number: int | None
    url: str
    show_url: str | None
    season_url: str | None
    similarity: float
    already_used: bool = False
    # Which of the show's episodes are the ones using it. `already_used` is
    # whether there are any, kept as its own field because that is what the
    # choices are filtered on and a caller reading only the flag should not have
    # to count a list to get it.
    used_by: list[EpisodeUsingTmdb] = []


# TODO: Validate
class UnmatchedEpisodeOutput(BaseModel):
    """An episode no TMDB record was found for, beside the closest TMDB episode."""

    id: uuid.UUID
    canonical_episode_id: uuid.UUID | None
    canonical_episode_note: str | None
    name: str | None
    episode_number: int | None
    absolute_number: int | None
    season_id: uuid.UUID
    season_name: str | None
    season_number: int | None
    show_id: uuid.UUID
    show_name: str | None
    show_year: int | None
    show_url: str | None
    season_url: str | None
    source_id: uuid.UUID
    source_name: str | None
    plugin_name: str | None
    url: str | None
    best_match: TmdbEpisodeChoice | None


# TODO: Validate
class UnlockedEpisodeOutput(UnmatchedEpisodeOutput):
    """An episode whose TMDB link no `User` has settled, matched or not.

    Unlike `UnmatchedEpisodeOutput` this covers the episodes that were linked as
    well, since a link made by name is exactly what a wrong name gets wrong, and
    a wrong link is only visible next to the TMDB episode it was made against.
    """

    name_matches: bool
    """Whether the website and TMDB give the episode the very same name.

    An episode both agree on is locked as it is stored, so one that is named the
    same and still unlocked is one they disagree about the number of, which is
    the pair worth looking at first.
    """


# TODO: Validate
class EpisodeTmdbUrlInput(BaseModel):
    """The themoviedb.org address a `User` is pointing an `Episode` at."""

    url: str


# TODO: Validate
class EpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[EpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class CanonicalEpisodeOutput(BaseCanonicalEpisode):
    """Schema for returning a `Episode`.

    An episode hangs off its season by the same column a copy hangs off the
    copy's season by, so what is served as the canonical season is read off
    `season_id`. The name it is served under does not change.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    canonical_season_id: uuid.UUID = Field(validation_alias=AliasPath("season_id"))
    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        self.tmdb_id = tmdb_id_of(self.key, EPISODE_LEVEL)
        return self


# TODO: Validate
class CanonicalEpisodeListOutput(CanonicalEpisodeOutput):
    """Schema for returning a list of `Episode`s, with what holds them."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    canonical_season_name: str | None = Field(
        validation_alias=AliasPath("season", "name"),
    )
    canonical_show_id: uuid.UUID = Field(
        validation_alias=AliasPath("season", "show_id"),
    )
    canonical_show_name: str | None = Field(
        validation_alias=AliasPath("season", "show", "name"),
    )
    canonical_show_key: str | None = Field(
        validation_alias=AliasPath("season", "show", "key"),
    )


# TODO: Validate
class CanonicalEpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[CanonicalEpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
