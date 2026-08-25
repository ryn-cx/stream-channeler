# TODO: Validate
"""Episode schemas."""

import uuid
from datetime import datetime
from typing import Self

from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from app.canonical_media.keys import EPISODE_LEVEL, tmdb_id_of
from app.episodes.models import BaseCanonicalEpisode, BaseEpisode, Episode
from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseInput,
    BaseUpdateWithKey,
    ReadOptions,
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

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    id: uuid.UUID
    season_id: uuid.UUID
    # The episode this is a link to, which is what the record is served as and
    # what a watch, a channel filter and a saved position all name. Nothing when
    # the row is the episode itself, which is what the admin lists serve
    # alongside the links.
    canonical_episode_id: uuid.UUID | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "canonical_episode_id",
            "sole_canonical_episode_id",
        ),
    )
    # Every episode it stands for, which is what the screens that settle the
    # links by hand work on: one of them is what the field above reads as, and a
    # row standing for two has none to read there at all.
    canonical_episode_ids: list[uuid.UUID] = Field(default_factory=list)
    # Where the row sits, as the link that was made for it says. `sort_order` is
    # the row's own column, which is what a website filed it under and what a row
    # with no link is ordered by; this is what the link holding it says instead.
    linked_sort_order: int | None = None
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
    show_id: uuid.UUID
    show_name: str | None
    url: str | None
    key: str
    canonical_episode_validated_at: datetime | None
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
    canonical_episode_validated_at: datetime | None
    canonical_episode_note: str | None
    issue_reports: list[IssueReportOutput]
    source: EpisodeInformationSide
    tmdb: EpisodeInformationSide | None
    user_url: str | None


# TODO: Validate
class UserEpisodeUrlInput(BaseInput):
    url: str = Field(min_length=1)


# TODO: Validate
class UserEpisodeUrlOutput(BaseModel):
    canonical_episode_id: uuid.UUID
    url: str | None


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
    # The rows themselves, so the match can be opened on its own page here the same way
    # the episode beside it can. TMDB's records are canonical rows, so these are the ids
    # of the very rows, not of non-canonical rows of them.
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
    duration: int | None
    air_date: datetime | None
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
class UnmatchedEpisodeOutput(EpisodeOutput):
    """An episode no TMDB record was found for, beside the closest TMDB episode."""

    absolute_number: int | None = None
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
    best_match: TmdbEpisodeChoice | None
    # The episode TMDB numbers the same way, which is a different question to
    # the one the name asks and often a different episode. Both are offered so
    # a row can be settled on whichever of the two is the one to trust.
    season_episode_match: TmdbEpisodeChoice | None
    absolute_number_match: TmdbEpisodeChoice | None


# TODO: Validate
class UnmatchedReadOptions(ReadOptions):
    non_canonical_shows_only: bool = False


# TODO: Validate
class UnmatchedEpisodesPublic(BaseModel):
    """Schema for returning a page of episodes waiting on a TMDB match."""

    data: list[UnmatchedEpisodeOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


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
class DuplicatedLinkEpisodeOutput(EpisodeOutput):
    """One of the episodes that collided on a canonical episode.

    Served as the whole row rather than as a name and a number, since the window
    opened to correct one of them edits the row itself.
    """

    season_number: int | None = None


# TODO: Validate
class DuplicatedCanonicalEpisodeOutput(BaseModel):
    """A canonical episode more than one episode of a single source is linked to.

    TMDB is what a title is usually canonical against, but a canonical row of any
    provider can be pointed at twice, so what is served is the canonical episode
    itself and the source that collided on it rather than anything TMDB's own.
    """

    id: str
    """The canonical episode and the source together, since a row is the pair."""

    canonical_episode_id: uuid.UUID
    season_id: uuid.UUID
    show_id: uuid.UUID
    key: str
    name: str | None
    season_number: int | None
    episode_number: int | None
    show_name: str | None
    show_year: int | None
    url: str | None
    show_url: str | None
    canonical_source_name: str | None
    canonical_plugin_name: str | None
    source_id: uuid.UUID
    source_name: str | None
    plugin_name: str | None
    linked_episodes: list[DuplicatedLinkEpisodeOutput]


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

    An episode hangs off its season by the same column a non-canonical row hangs off the
    non-canonical row's season by, so what is served as the canonical season is read off
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
