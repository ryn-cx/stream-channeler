# TODO: Validate
from __future__ import annotations

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
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.schemas import BaseInput, BasePatchInputWithoutKey
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourcePublic


class ChannelPostInput(BaseInput, BaseChannel):
    pass


class ChannelPatchInput(BasePatchInputWithoutKey[Channel], BaseChannel):
    public: bool | None = Field(default=None)  # type: ignore[assignment]
    default_order: str | None = Field(default=None)


class ChannelOutput(BaseChannel):
    id: uuid.UUID
    user_id: uuid.UUID


class ChannelQueueOutput(BaseChannelQueue):
    id: uuid.UUID
    channel_id: uuid.UUID


class EpisodeWithExtrasOutput(EpisodeOutput):
    watch_date: datetime | None = Field(default=None)
    verified: bool | None = Field(default=None)
    episode_watch_id: uuid.UUID | None = Field(default=None)
    channel_id: uuid.UUID


class ChannelEpisodesOutput(BaseModel):
    episodes: list[EpisodeWithExtrasOutput]
    seasons: dict[uuid.UUID, SeasonOutput]
    shows: dict[uuid.UUID, ShowPublic]
    sources: dict[uuid.UUID, SourcePublic]
    plugins: dict[uuid.UUID, PluginOutput]
    channels: dict[uuid.UUID, ChannelOutput]


class ChannelShowsOutput(BaseModel):
    shows: list[ShowPublic] = Field(default_factory=list)
    sources: dict[uuid.UUID, SourcePublic] = Field(default_factory=dict)


class WhitelistEntryInput(BaseInput):
    id: uuid.UUID
    marked: bool


class WhitelistShowInput(BaseInput):
    whitelist_mode: bool | None = Field(default=None)
    seasons: list[WhitelistEntryInput] = Field(default_factory=list)
    episodes: list[WhitelistEntryInput] = Field(default_factory=list)


class WhitelistShowOutput(ShowPublic):
    whitelist_mode: bool
    enabled_season_ids: list[uuid.UUID]
    enabled_episode_ids: list[uuid.UUID]
    seasons: list[SeasonOutput]
    episodes: list[EpisodeOutput]


# region Episode Configuration


class SortOptionOutput(BaseModel):
    label: str
    model: Literal["episode", "season", "show", "source", "plugin"]
    field: str


class SortKeyInput(BaseInput):
    # Redeclaring model_config replaces (not merges with) BaseInput's config, so
    # both settings have to be listed here.
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
    # order controls how this key contributes to the final ordering:
    # - "sequential": standard ORDER BY contribution using the value itself.
    # - "interleave": partition rows by this value and spread them across the
    #   output using row_number, so rows with distinct values alternate.
    # - "randomize": like interleave but partitions play in a random order.
    order: Literal["sequential", "interleave", "randomize"] = Field(
        default="sequential",
    )
    aggregation: Literal["max", "min", "avg"] | None = Field(default=None)
    days: int | None = Field(default=None)
    recently_aired_date: datetime | None = Field(default=None)

    @property
    def model_class(self) -> type[Episode | Season | Show | Source | Plugin]:
        return self._MODEL_MAP[self.model]

    @model_validator(mode="after")
    def validate_and_resolve(self) -> SortKeyInput:
        # "random" is the default sort fallback in episode_selector and is not
        # exposed as a user-facing option, so it is allowed but not declared in
        # any model's SORTABLE_FIELDS.
        if self.field == "random":
            return self
        if self.field not in self.model_class.SORTABLE_FIELDS:
            msg = f"Invalid field '{self.field}' for model '{self.model}'"
            raise ValueError(msg)
        return self


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
    random_seed: int = Field(default_factory=lambda: random.randint(0, 2**31))
    hide_watched: bool = Field(default=False)
    hide_unwatched: bool = Field(default=False)
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
    limit: int | None = Field(default=None, ge=1)


# endregion Episode Configuration
