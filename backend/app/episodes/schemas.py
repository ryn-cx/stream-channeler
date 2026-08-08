# TODO: Validate
"""Episode schemas."""

import uuid
from datetime import datetime

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.episodes.models import BaseEpisode, Episode
from app.issue_reports.schemas import IssueReportOutput
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
    sort_order: int | None
    season_number: int | None
    season_name: str | None
    show_name: str | None
    url: str | None
    key: str
    episode_identifier: str
    episode_identifier_locked: bool
    episode_identifier_note: str | None
    data_timestamp: datetime | None
    update_at: datetime | None
    modified_at: datetime | None


class EpisodeInformationOutput(BaseModel):
    """What the website and TMDB each say about an episode, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    episode_id: uuid.UUID
    episode_identifier: str
    episode_identifier_locked: bool
    episode_identifier_note: str | None
    issue_reports: list[IssueReportOutput]
    source: EpisodeInformationSide
    tmdb: EpisodeInformationSide | None


class TmdbEpisodeChoice(BaseModel):
    """A TMDB episode of a title, as one of the episodes an `Episode` can be linked to.

    `absolute_number` counts the episode from the first of the title rather than
    from the first of its own season, which is how a website that never restarts
    its numbering names the same episode. Specials are outside that count and
    have none.

    `similarity` is how much of its name it shares with the episode being linked,
    which is what lets the choices be read in the order they are most likely to
    be the one rather than in the order the title runs.
    """

    tmdb_episode_id: int
    name: str | None
    season_number: int | None
    episode_number: int | None
    absolute_number: int | None
    url: str | None
    similarity: float
    already_used: bool = False
    """Whether another episode of the same show is already pointed at this one.

    A TMDB episode stands for one episode of the title, so one already spoken
    for is rarely the answer for a second, and saying so is what lets the ones
    still going spare be the ones offered first.
    """


class UnmatchedEpisodeOutput(BaseModel):
    """An episode no TMDB record was found for, beside the closest TMDB episode."""

    id: uuid.UUID
    episode_identifier: str
    name: str | None
    episode_number: int | None
    absolute_number: int | None
    season_name: str | None
    season_number: int | None
    show_name: str | None
    source_name: str | None
    url: str | None
    best_match: TmdbEpisodeChoice | None


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


class EpisodeTmdbLinkInput(BaseModel):
    """The TMDB episode a `User` is pointing an `Episode` at by hand."""

    tmdb_episode_id: int
    selected: bool = False
    """Whether the `User` went and found this episode rather than taking the offer.

    Confirming the closest match says only that what was suggested looked right,
    where picking one out of the title is somebody having looked for it, so the
    two are worth telling apart when the link is read back later.
    """


class EpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[EpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
