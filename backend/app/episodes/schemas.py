# TODO: Validate
"""Episode schemas."""

import uuid
from datetime import datetime
from typing import Self, override

from pydantic import (
    AliasChoices,
    AliasPath,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)
from sqlmodel import Session

from app.episodes.models import BaseEpisode, BaseTmdbEpisode, Episode
from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseInput,
    BaseUpdateWithKey,
    ReadOptions,
    make_model_with_all_fields_optional,
)
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.sources.schemas import SourceListPublic
from app.titles.schemas import TitlePublic
from app.tmdb_media.tmdb import (
    get_tmdb_id,
    is_tmdb_key,
    tmdb_episode_url,
    tmdb_season_url,
)


# TODO: Validate
class EpisodeCreate(BaseCreateWithParentAndKey[Episode, Season], BaseEpisode):
    """Schema for creating an `Episode`."""


# TODO: Validate
class EpisodeUpdate(
    make_model_with_all_fields_optional(BaseEpisode),
    BaseUpdateWithKey[Episode],
):
    """Schema for updating an `Episode`."""

    tmdb_episode_note: str | None = None

    # TODO: Validate
    @override
    def update(self, session: Session, existing_record: Episode) -> Episode:
        # The note is a column of the links rather than of the episode, so the
        # generic update - which writes the episode's own columns and nothing
        # else - passes over it and it is written here instead.
        if "tmdb_episode_note" in self.model_fields_set:
            existing_record.tmdb_episode_note = self.tmdb_episode_note
        return super().update(session, existing_record)


# TODO: Validate
class EpisodeOutput(BaseEpisode):
    """Schema for returning an `Episode`."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    id: uuid.UUID
    season_id: uuid.UUID
    modified_at: datetime
    tmdb_episode_note: str | None = None
    tmdb_episode_id: uuid.UUID | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "tmdb_episode_id",
            "sole_tmdb_episode_id",
        ),
    )
    tmdb_episode_ids: list[uuid.UUID] = Field(default_factory=list)
    tmdb_id: int | None = None
    tmdb_url: str | None = None


# TODO: Consider reworking this into seperate models for each parent.
# TODO: Validate
class EpisodeListOutput(EpisodeOutput):
    """Schema for returning a list of `Episode`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    season_name: str | None = Field(validation_alias=AliasPath("season", "name"))
    season_number: int | None = Field(
        validation_alias=AliasPath("season", "season_number"),
    )
    title_id: uuid.UUID = Field(validation_alias=AliasPath("season", "title_id"))
    title_name: str | None = Field(
        validation_alias=AliasPath("season", "title", "name"),
    )
    source_id: uuid.UUID = Field(
        validation_alias=AliasPath("season", "title", "source_id"),
    )
    source_key: str = Field(
        validation_alias=AliasPath("season", "title", "source", "key"),
    )
    source_favicon_url: str | None = Field(
        validation_alias=AliasPath("season", "title", "source", "favicon_url"),
    )
    plugin_id: uuid.UUID = Field(
        validation_alias=AliasPath("season", "title", "source", "plugin_id"),
    )
    plugin_name: str | None = Field(
        validation_alias=AliasPath("season", "title", "source", "plugin", "key"),
    )


# TODO: Validate
class EpisodeRecord(BaseModel):
    """An `Episode` and everything above it, each served as the record it is.

    The season, the title and the website are handed over whole rather than
    picked apart into a name and a number, so a screen reading any of them reads
    the same shape it would have been served on its own page.
    """

    episode: EpisodeOutput
    season: SeasonOutput
    title: TitlePublic
    source: SourceListPublic

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        if is_tmdb_key(self.episode.key):
            self.episode.tmdb_id = get_tmdb_id(self.episode.key)
        self.episode.tmdb_url = tmdb_episode_url(
            self.title.key,
            self.season.season_number,
            self.episode.episode_number,
        )
        self.season.tmdb_url = tmdb_season_url(
            self.title.key,
            self.season.season_number,
        )
        return self


# TODO: Validate
class TmdbEpisodeRecord(EpisodeRecord):
    absolute_number: int | None


# TODO: Validate
class EpisodeInformationSide(EpisodeRecord):
    label: str
    url: str | None
    absolute_number: int | None


# TODO: Validate
class EpisodeInformationOutput(BaseModel):
    """What the website and TMDB each say about an episode, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    episode_id: uuid.UUID
    tmdb_episode_validated_at: datetime | None
    tmdb_episode_note: str | None
    issue_reports: list[IssueReportOutput]
    source: EpisodeInformationSide
    tmdb: EpisodeInformationSide | None
    user_url: str | None


# TODO: Validate
class EpisodeDatabaseColumn(BaseModel):
    name: str
    value: str | None


# TODO: Validate
class EpisodeDatabaseRow(BaseModel):
    episode_id: uuid.UUID
    label: str
    columns: list[EpisodeDatabaseColumn]


# TODO: Validate
class EpisodeDatabaseOutput(BaseModel):
    episode: EpisodeDatabaseRow
    tmdb_episodes: list[EpisodeDatabaseRow]


# TODO: Validate
class UserEpisodeUrlInput(BaseInput):
    url: str = Field(min_length=1)


# TODO: Validate
class UserEpisodeUrlOutput(BaseModel):
    tmdb_episode_id: uuid.UUID
    url: str | None


# TODO: Validate
class TmdbEpisodeChoice(EpisodeRecord):
    absolute_number: int | None
    similarity: float
    from_title: bool = True
    already_used: bool = False
    # Which of the title's episodes are the ones using it. `already_used` is
    # whether there are any, kept as its own field because that is what the
    # choices are filtered on and a caller reading only the flag should not have
    # to count a list to get it.
    used_by: list[EpisodeRecord] = []


# TODO: Validate
class UnmatchedEpisodeOutput(EpisodeRecord):
    """An episode no TMDB record was found for, beside the closest TMDB episode."""

    absolute_number: int | None = None
    season_episode_match: TmdbEpisodeChoice | None
    absolute_number_match: TmdbEpisodeChoice | None
    episode_number_absolute_match: TmdbEpisodeChoice | None
    description_embedding_matches: list[TmdbEpisodeChoice] = []
    description_tfidf_matches: list[TmdbEpisodeChoice] = []
    title_embedding_matches: list[TmdbEpisodeChoice] = []
    title_tfidf_matches: list[TmdbEpisodeChoice] = []


# TODO: Validate
class UnmatchedReadOptions(ReadOptions):
    linked_titles_only: bool = False
    in_user_channels_only: bool = True


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

    best_match: TmdbEpisodeChoice | None
    name_matches: bool
    """Whether the website and TMDB give the episode the very same name.

    An episode both agree on is locked as it is stored, so one that is named the
    same and still unlocked is one they disagree about the number of, which is
    the pair worth looking at first.
    """


# TODO: Validate
class DuplicatedTmdbEpisodeOutput(BaseModel):
    """A canonical episode more than one episode of a single source is linked to.

    TMDB is what a title is usually canonical against, but a canonical row of any
    provider can be pointed at twice, so what is served is the canonical episode
    itself and the source that collided on it rather than anything TMDB's own.
    """

    id: str
    """The canonical episode and the source together, since a row is the pair."""

    tmdb: EpisodeRecord
    source: SourceListPublic
    linked_episodes: list[EpisodeRecord]


# TODO: Validate
class EpisodeTmdbUrlInput(BaseModel):
    """The themoviedb.org address a `User` is pointing an `Episode` at."""

    url: str


# TODO: Validate
class EpisodeTmdbLinkInput(BaseModel):
    episode_id: uuid.UUID
    tmdb_episode_id: uuid.UUID


# TODO: Validate
class EpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[EpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class TmdbEpisodeOutput(BaseTmdbEpisode):
    """Schema for returning a `Episode`.

    An episode hangs off its season by the same column a non-canonical row hangs off the
    non-canonical row's season by, so what is served as the canonical season is read off
    `season_id`. The name it is served under does not change.
    """

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    tmdb_season_id: uuid.UUID = Field(validation_alias=AliasPath("season_id"))
    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        if is_tmdb_key(self.key):
            self.tmdb_id = get_tmdb_id(self.key)
        return self


# TODO: Validate
class TmdbEpisodeListOutput(TmdbEpisodeOutput):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    tmdb_season_name: str | None = Field(
        validation_alias=AliasPath("season", "name"),
    )
    tmdb_title_id: uuid.UUID = Field(
        validation_alias=AliasPath("season", "title_id"),
    )
    tmdb_title_name: str | None = Field(
        validation_alias=AliasPath("season", "title", "name"),
    )
    tmdb_title_key: str | None = Field(
        validation_alias=AliasPath("season", "title", "key"),
    )


# TODO: Validate
class TmdbEpisodesPublic(BaseModel):
    """Schema for returning a list of `Episode`s."""

    data: list[TmdbEpisodeListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
