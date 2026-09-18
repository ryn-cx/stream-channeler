# TODO: Validate
"""Title schemas."""

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

from app.issue_reports.schemas import IssueReportOutput
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    ReadOptions,
    make_model_with_all_fields_optional,
)
from app.sources.models import Source
from app.sources.schemas import SourceListPublic
from app.titles.models import BaseTitle, BaseTmdbTitle, Title
from app.tmdb_media.tmdb import (
    get_tmdb_id,
    is_tmdb_key,
    tmdb_title_url,
)


# TODO: Validate
class TitleCreate(BaseCreateWithParentAndKey[Title, Source], BaseTitle):
    """Schema for creating a `Title`."""


# TODO: Validate
class TitleUpdate(
    make_model_with_all_fields_optional(BaseTitle),
    BaseUpdateWithKey[Title],
):
    """Schema for updating a `Title`."""


# TODO: Validate
class WatchProviderOffering(BaseModel):
    region: str
    tmdb_provider_id: int
    provider_name: str
    logo_url: str | None
    offering_type: str


# TODO: Validate
class TmdbEpisodeGroupOption(BaseModel):
    id: str
    name: str
    description: str | None
    group_count: int
    episode_count: int
    type: int


# TODO: Validate
class TitlePublic(BaseTitle):
    """Schema for returning a `Title`."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    source_id: uuid.UUID
    id: uuid.UUID
    # The canonical title this stands for, which is what groups two websites' rows
    # into one card and what the channel's per-title stats are keyed by. A row that
    # mixes titles stands for each of them as much as for any other and so has none
    # to be read under here; where a channel is what is being served, the
    tmdb_title_id: uuid.UUID | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "tmdb_title_id",
            "sole_tmdb_title_id",
        ),
    )
    # Every canonical title it stands for, which is what the screens that settle
    # the links by hand work on: one of them is what the field above reads as,
    # and a row standing for two has none to read there at all.
    tmdb_title_ids: list[uuid.UUID] = Field(default_factory=list)
    # The TMDB id behind that, when TMDB has a record of it.
    tmdb_id: int | None = None
    # The row's own page on themoviedb.org, read back out of its own key, so a
    # row TMDB issued carries one and a website's row carries none.
    tmdb_url: str | None = None
    plugin_name: str | None = Field(
        default=None,
        validation_alias=AliasPath("source", "plugin", "key"),
    )

    # TODO: Validate
    @model_validator(mode="after")
    def _read_own_key(self) -> Self:
        self.tmdb_url = tmdb_title_url(self.key)
        return self


# TODO: Consider reworking this into seperate models for each parent.
# TODO: Validate
class TitleListPublic(TitlePublic):
    """Schema for returning a list of `Title`s, with parent information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    source_key: str = Field(validation_alias=AliasPath("source", "key"))
    plugin_id: uuid.UUID = Field(validation_alias=AliasPath("source", "plugin_id"))
    plugin_name: str | None = Field(
        validation_alias=AliasPath("source", "plugin", "key"),
    )


# TODO: Validate
class TitleRecord(BaseModel):
    title: TitlePublic
    source: SourceListPublic


# TODO: Validate
class TitleInformationSide(TitleRecord):
    label: str


# TODO: Validate
class TitleInformationOutput(BaseModel):
    """What the website and TMDB each say about a title, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    editable: bool
    issue_reports: list[IssueReportOutput]
    source: TitleInformationSide
    tmdb: TitleInformationSide | None


# TODO: Validate
class TitleTmdbUrlInput(BaseModel):
    url: str


# TODO: Validate
class TitleImportUrlInput(BaseModel):
    url: str


# TODO: Validate
class TitlesPublic(BaseModel):
    """Schema for returning a list of `Title`s."""

    data: list[TitleListPublic]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class TmdbTitleOutput(BaseTmdbTitle):
    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None
    tmdb_url: str | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        if is_tmdb_key(self.key):
            self.tmdb_id = get_tmdb_id(self.key)
        self.tmdb_url = tmdb_title_url(self.key)
        return self


# TODO: Validate
class TmdbTitlesPublic(BaseModel):
    """Schema for returning a list of `Title`s."""

    data: list[TmdbTitleOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class UnvalidatedLinkedTitleOutput(BaseModel):
    """One of the canonical titles an unvalidated row stands for.

    Enough of the canonical title to judge the link by, since what is being
    settled is whether this row really is that title.
    """

    id: uuid.UUID
    name: str | None
    year: int | None
    url: str | None
    image_url: str | None
    tmdb_id: int | None
    note: str | None


# TODO: Validate
class UnvalidatedTitleOutput(TitleListPublic):
    linked_titles: list[UnvalidatedLinkedTitleOutput]
    episode_count: int
    created_at: datetime


# TODO: Validate
class UnmatchedTitleOutput(BaseModel):
    id: uuid.UUID
    provider_name: str
    plugin_key: str | None
    created_at: datetime
    modified_at: datetime
    title_id: uuid.UUID
    title_name: str | None
    title_year: int | None
    media_type: str | None
    tmdb_url: str | None
    channel_count: int
    episode_count: int


# TODO: Validate
class UnmatchedTitlesPublic(BaseModel):
    """Schema for returning a page of titles waiting on a source."""

    data: list[UnmatchedTitleOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class UnmatchedTitleReadOptions(ReadOptions):
    in_user_channels_only: bool = True
    include_ignored: bool = False


# TODO: Validate
class UnmatchedTitleImport(BaseModel):
    url: str = Field(min_length=1)
