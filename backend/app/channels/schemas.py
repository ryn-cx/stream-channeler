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
)
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.models import Visibility
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import BaseInput, BaseUpdateWithoutKey
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic


class ChannelCreate(BaseInput, BaseChannel):
    """Schema for creating a `Channel`."""


class ChannelUpdate(BaseUpdateWithoutKey[Channel], BaseChannel):
    """Schema for updating a `Channel`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    visibility: Visibility | None = Field(default=None)  # type: ignore[assignment]


class ChannelOutput(BaseChannel):
    """Schema for returning a `Channel`."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    score: int


class ChannelPublicOutput(BaseChannel):
    """Schema for returning a publicly listed `Channel`."""

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None


class ChannelPublicListOutput(BaseModel):
    """Schema for returning a page of publicly listed `Channel`s."""

    data: list[ChannelPublicOutput]
    count: int


class ChannelAdminOutput(ChannelOutput):
    """Schema for returning a `Channel` to an admin, including the owner username."""

    username: str | None


class ChannelAdminUpdate(BaseInput, BaseChannel):
    """Schema for an admin updating any field on a `Channel`."""

    visibility: Visibility | None = Field(default=None)  # type: ignore[assignment]
    score: int | None = Field(default=None)


class ChannelQueueOutput(BaseChannelQueue):
    id: uuid.UUID
    channel_id: uuid.UUID


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


class ChannelShowsOutput(BaseModel):
    shows: list[ShowPublic] = Field(default_factory=list)
    # Shows that don't belong to the channel but carry blacklist/whitelist entries for
    # episodes pulled in from other channels.
    filter_only_shows: list[ShowPublic] = Field(default_factory=list)
    sources: dict[uuid.UUID, SourcePublic] = Field(default_factory=dict)


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

    additional_channels: list[uuid.UUID] = Field(default_factory=list)
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
