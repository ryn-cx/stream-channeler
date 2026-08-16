# TODO: Validate
"""Show schemas."""

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

from app.canonical_media.keys import SHOW_LEVEL, tmdb_id_of
from app.issue_reports.schemas import IssueReportOutput
from app.media.canonical_metadata import tmdb_show_url
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.shows.models import BaseCanonicalShow, BaseShow, Show
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
class TmdbEpisodeGroupOption(BaseModel):
    """One of the episode orders TMDB holds for a title.

    What the order is and how big it is, which is all that choosing between them
    needs. The episodes each order puts where is a file of its own and is only
    read once an order has been chosen.
    """

    id: str
    name: str
    description: str | None
    group_count: int
    episode_count: int
    type: int


# TODO: Validate
class ShowPublic(BaseShow):
    """Schema for returning a `Show`."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    source_id: uuid.UUID
    id: uuid.UUID
    # The canonical show this stands for, which is what groups two websites' rows
    # into one card and what the channel's per-show stats are keyed by. A row that
    # mixes shows stands for each of them as much as for any other and so has none
    # to be read under here; where a channel is what is being served, the
    # canonical show it holds the row under is handed in instead.
    canonical_show_id: uuid.UUID | None = Field(
        default=None,
        validation_alias=AliasChoices(
            "canonical_show_id",
            "sole_canonical_show_id",
        ),
    )
    # The TMDB id behind that, when TMDB has a record of it.
    tmdb_id: int | None = None


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
    """One record's own account of a show, as the website holding it has it."""

    label: str
    name: str | None
    media_type: str | None
    description: str | None
    image_url: str | None
    url: str | None
    key: str


# TODO: Validate
class ShowInformationOutput(BaseModel):
    """What the website and TMDB each say about a show, side by side.

    The stored record is returned as the website reported it rather than as it is
    served, so the two accounts can be compared instead of one standing in for
    the other.
    """

    show_id: uuid.UUID
    canonical_show_locked: bool
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


# TODO: Validate
class CanonicalShowOutput(BaseCanonicalShow):
    """Schema for returning a `Show`.

    `tmdb_id` and `tmdb_url` are read back out of `key` rather than stored, since
    the key is the whole of what says which TMDB record a show is. They are
    served for reading only: nothing can be sorted or filtered by a value the
    database does not hold a column for.
    """

    id: uuid.UUID
    created_at: datetime
    modified_at: datetime

    tmdb_id: int | None = None
    tmdb_url: str | None = None

    # TODO: Validate
    @model_validator(mode="after")
    def _read_key(self) -> Self:
        self.tmdb_id = tmdb_id_of(self.key, SHOW_LEVEL)
        self.tmdb_url = tmdb_show_url(self.key)
        return self


# TODO: Validate
class CanonicalShowsPublic(BaseModel):
    """Schema for returning a list of `Show`s."""

    data: list[CanonicalShowOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
