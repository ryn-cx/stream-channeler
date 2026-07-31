# TODO: Validate
import json
import random
import uuid
from datetime import datetime
from typing import ClassVar, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator
from pydantic.alias_generators import to_camel
from sqlmodel import Field

from app.channels.models import (
    BaseChannel,
    BaseChannelQueue,
    Channel,
    URLStatus,
)
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import (
    BaseInput,
    BaseUpdateWithoutKey,
    RecordScope,
    ScopedReadOptions,
    make_model_with_all_fields_optional,
)
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic


class ChannelCreate(BaseInput, BaseChannel):
    """Schema for creating a `Channel`."""


class ChannelUpdate(
    make_model_with_all_fields_optional(BaseChannel),
    BaseUpdateWithoutKey[Channel],
):
    """Schema for updating a `Channel`."""


class ChannelOutput(BaseChannel):
    """Schema for returning a `Channel`.

    `user_id` and `username` are redacted on anonymous `Channel`s unless the viewer
    owns the record or is an admin.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None = None
    score: int


class ChannelListOutput(BaseChannel):
    """Schema for returning a `Channel` alongside its owner.

    `user_id` and `username` are redacted on anonymous `Channel`s unless the viewer
    owns the record or is an admin. `score` is not a secret, so one row shape serves
    every scope and every viewer.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None
    score: int
    # The viewer's private overrides, only populated in the `favorites` scope. Each
    # is `None` when unset; the frontend falls back to the shared field above.
    custom_name: str | None = None
    custom_channel_number: float | None = None


class ChannelFavoriteUpdate(BaseInput):
    """Schema for a `User`'s private customization of a favorited `Channel`."""

    name: str | None = Field(default=None)
    channel_number: float | None = Field(default=None)


class ChannelPublicListOutput(BaseModel):
    """Schema for returning a page of publicly listed `Channel`s."""

    data: list[ChannelListOutput]
    count: int


class ChannelsPublic(BaseModel):
    """Schema for returning a page of `Channel`s."""

    data: list[ChannelListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


class ChannelReadOptions(ScopedReadOptions):
    """Read options for the `Channel` list.

    Defaults to `owned` rather than `ScopedReadOptions`'s `all`, so an unscoped read
    returns the `User`'s own `Channel`s instead of demanding admin rights.
    """

    scope: RecordScope = RecordScope.owned


class ChannelAdminUpdate(
    make_model_with_all_fields_optional(BaseChannel),
    BaseInput,
):
    """Schema for an admin updating any field on a `Channel`."""

    score: int | None = Field(default=None)


class CombinedChannelOutput(BaseModel):
    """Schema for returning a channel combined into another channel."""

    id: uuid.UUID
    name: str | None


class ChannelQueueOutput(BaseChannelQueue):
    id: uuid.UUID
    channel_id: uuid.UUID


class ChannelQueueAdminOutput(ChannelQueueOutput):
    """Schema for returning a queue entry to an admin, with channel and owner info."""

    created_at: datetime
    channel_name: str | None
    channel_number: float | None
    user_id: uuid.UUID | None
    username: str | None


class ChannelQueueAdminUpdate(BaseInput):
    """Schema for an admin updating a `Channel`'s queue entry."""

    status: URLStatus | None = Field(default=None)
    note: str | None = Field(default=None)


class ChannelOrderInput(BaseInput):
    """Schema for setting the custom episode order of a `Channel`."""

    episode_ids: list[uuid.UUID] = Field(default_factory=list)


class EpisodeWithDetails(EpisodeOutput):
    watch_date: datetime | None = Field(default=None)
    verified: bool | None = Field(default=None)
    episode_watch_id: uuid.UUID | None = Field(default=None)
    channel_id: uuid.UUID
    # All in-scope member channels this episode belongs to. The first is `channel_id`
    # (the primary/base channel). Used by the blacklist UI to offer each as a target.
    channel_ids: list[uuid.UUID] = Field(default_factory=list)


class ChannelEpisodesOutput(BaseModel):
    episodes: list[EpisodeWithDetails]
    seasons: dict[uuid.UUID, SeasonOutput]
    shows: dict[uuid.UUID, ShowPublic]
    sources: dict[uuid.UUID, SourcePublic]
    plugins: dict[uuid.UUID, PluginOutput]
    channels: dict[uuid.UUID, ChannelOutput]


class ChannelShowGroup(BaseModel):
    """The regular shows contributed by one channel within a combined channel."""

    channel_id: uuid.UUID
    channel_name: str | None
    shows: list[ShowPublic] = Field(default_factory=list)


class ChannelShowsOutput(BaseModel):
    shows: list[ShowPublic] = Field(default_factory=list)
    # Shows that don't belong to the channel but carry blacklist/whitelist entries for
    # episodes pulled in from other channels.
    filter_only_shows: list[ShowPublic] = Field(default_factory=list)
    sources: dict[uuid.UUID, SourcePublic] = Field(default_factory=dict)
    # The regular shows grouped by the channel they come from, with the channel this
    # endpoint was called on first and combined channels after it, sorted by name.
    groups: list[ChannelShowGroup] = Field(default_factory=list)


class WhitelistEntryInput(BaseInput):
    id: uuid.UUID
    marked: bool
    # Only meaningful for episode entries; ignored for seasons. `None` = never expires.
    expires_at: datetime | None = Field(default=None)


class BlacklistEpisodeInput(BaseInput):
    show_id: uuid.UUID
    episode_id: uuid.UUID
    expires_at: datetime | None = Field(default=None)


class WhitelistShowInput(BaseInput):
    is_whitelist: bool | None = Field(default=None)
    seasons: list[WhitelistEntryInput] = Field(default_factory=list)
    episodes: list[WhitelistEntryInput] = Field(default_factory=list)


class WhitelistSeasonOutput(SeasonOutput):
    filtered: bool


class WhitelistEpisodeOutput(EpisodeOutput):
    filtered: bool
    expires_at: datetime | None = Field(default=None)


class WhitelistShowOutput(ShowPublic):
    is_whitelist: bool
    seasons: list[WhitelistSeasonOutput]
    episodes: list[WhitelistEpisodeOutput]


class SortOptionOutput(BaseModel):
    label: str
    model: Literal["episode", "season", "show", "source", "plugin"]
    field: str


class SortKeyInput(BaseInput):
    model_config = ConfigDict(
        validate_by_name=True,
        extra="forbid",
        alias_generator=to_camel,
    )  # type: ignore[reportAssignmentType]

    _MODEL_MAP: ClassVar[dict[str, type[Episode | Season | Show | Source | Plugin]]] = {
        "episode": Episode,
        "season": Season,
        "show": Show,
        "source": Source,
        "plugin": Plugin,
    }

    model: Literal["episode", "season", "show", "source", "plugin"]
    field: str
    direction: Literal["ascending", "descending"]
    order: Literal["sequential", "interleave", "randomize"] = Field()
    aggregation: Literal["max", "min", "avg"] | None = Field(default=None)
    days: int | None = Field(default=None)
    recently_aired_date: datetime | None = Field(default=None)
    fuzziness: int | None = Field(default=None, ge=0)

    @property
    def model_class(self) -> type[Episode | Season | Show | Source | Plugin]:
        return self._MODEL_MAP[self.model]

    @model_validator(mode="after")
    def validate_and_resolve(self) -> SortKeyInput:
        if self.field == "random" or self.field in self.model_class.SORTABLE_FIELDS:
            return self

        msg = f"Invalid field '{self.field}' for model '{self.model}'"
        raise ValueError(msg)


class ChannelOptions(BaseInput):
    model_config = ConfigDict(
        validate_by_name=True,
        extra="forbid",
        alias_generator=to_camel,
    )  # type: ignore[reportAssignmentType]

    sort_by: list[SortKeyInput] = Field(default_factory=list)

    @field_validator("sort_by", mode="before")
    @classmethod
    def _load_sort_keys(cls, value: object) -> object:
        return [
            SortKeyInput.model_validate(
                json.loads(item) if isinstance(item, str) else item,
            )
            for item in value  # type: ignore[attr-defined]
        ]

    order_preset_id: uuid.UUID | None = Field(default=None)
    source_ids: list[uuid.UUID] = Field(default_factory=list)
    source_ids_is_blacklist: bool = Field(default=False)
    random_seed: int = Field(default_factory=lambda: random.randint(0, 2**31))  # noqa: S311 - TODO: Confirm non-cryptographic random is acceptable
    hide_watched: bool = Field(default=False)
    hide_unwatched: bool = Field(default=False)
    hide_partially_watched: bool = Field(default=False)
    maximum_watch_date_absolute: datetime | None = Field(default=None)
    minimum_air_date_absolute: datetime | None = Field(default=None)
    maximum_air_date_absolute: datetime | None = Field(default=None)
    minimum_release_date_absolute: datetime | None = Field(default=None)
    maximum_release_date_absolute: datetime | None = Field(default=None)
    maximum_watch_date_relative: int | None = Field(default=None)
    minimum_air_date_relative: int | None = Field(default=None)
    maximum_air_date_relative: int | None = Field(default=None)
    minimum_release_date_relative: int | None = Field(default=None)
    maximum_release_date_relative: int | None = Field(default=None)
    total_shows_count: int | None = Field(default=None, ge=0)
    started_shows_count: int | None = Field(default=None, ge=0)
    new_shows_count: int | None = Field(default=None, ge=0)
    minimum_duration: int | None = Field(default=None)
    maximum_duration: int | None = Field(default=None)
    limit: int | None = Field(default=1000, ge=1, le=1000)
