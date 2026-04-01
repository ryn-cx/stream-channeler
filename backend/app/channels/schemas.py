# TODO: Validate
import json
import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from pydantic import BaseModel, BeforeValidator, ConfigDict, model_validator
from pydantic import Field as PydanticField
from sqlmodel import Field, SQLModel

from app.channels.models import (
    BaseChannel,
    BaseChannelQueue,
    BaseChannelShow,
    Channel,
    ChannelQueue,
    ChannelShow,
)
from app.episodes.models import Episode
from app.episodes.schemas import EpisodeOutput
from app.plugins.models import Plugin
from app.plugins.schemas import PluginOutput
from app.seasons.models import Season
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowOutput
from app.sources.models import Source
from app.sources.schemas import SourceOutput
from app.users.models import User
from app.utils import tz_datetime


class ChannelInput(BaseChannel):
    def upsert(
        self,
        user: User,
        existing_channel: Channel | None,
    ) -> Channel:
        if existing_channel:
            existing_channel.sqlmodel_update(self.model_dump())
            return existing_channel
        channel = Channel.model_validate(self, update={"user_id": user.id})
        user.channels.append(channel)
        return channel


class ChannelPostInput(BaseChannel):
    model_config = ConfigDict(extra="forbid")


class ChannelPatchInput(SQLModel):
    model_config = ConfigDict(extra="forbid")
    name: str | None = Field(default=None)
    channel_number: int | None = Field(default=None)
    public: bool = Field(default=False)
    default_order: str | None = Field(default=None)


class ChannelOutput(BaseChannel):
    # When returning a list of channels there needs to be a way to identify the channel.
    id: uuid.UUID
    # When accessing a public page there needs to be a way to identify if the user owns
    # the channel so the UI can change based on that.
    user_id: uuid.UUID


class ChannelsListOutput(SQLModel):
    data: list[ChannelOutput]


# This schema is just used for inserting data into the database. It is not used for
# reading the user's input because it is simpler for the user to have the input just be
# a list of URLs.
class ChannelQueueInput(BaseChannelQueue):
    """Input schema for creating or updating a channel queue entry."""

    def upsert(
        self,
        channel: Channel,
        existing_entry: ChannelQueue | None = None,
        protected_keys: set[str] | None = None,
    ) -> ChannelQueue:
        """Insert or update a ChannelQueue entry.

        Args:
            channel: Parent channel instance
            existing_entry: Existing ChannelQueue instance to update.

        Returns:
            ChannelQueue instance (either newly created or updated)
        """
        if protected_keys is None:
            protected_keys = set()

        if existing_entry:
            # TODO: Use _update_existing_entry like other classes
            dumped = self.model_dump(exclude=protected_keys)
            # If no values are changed modified_at will not be autoamtically set,
            # the easy way to fix this is to just set it manually so there will
            # always be a changed value.
            dumped["modified_at"] = tz_datetime.now()
            return existing_entry.sqlmodel_update(dumped)

        entry = ChannelQueue.model_validate(self, update={"channel_id": channel.id})
        channel.queue.append(entry)
        return entry


class ChannelQueueOutput(BaseChannelQueue):
    id: uuid.UUID


class ChannelQueuesListOutput(SQLModel):
    data: list[ChannelQueueOutput]


class ChannelShowInput(BaseChannelShow):
    def upsert(
        self,
        channel: Channel,
        existing_entry: ChannelShow | None = None,
        protected_keys: set[str] | None = None,
    ) -> ChannelShow:
        """Insert or update a ChannelShow.

        Args:
            channel: Parent channel instance
            existing_entry: Existing ChannelShow instance to update.

        Returns:
            ChannelShowOutput instance (either newly created or updated)
        """
        if protected_keys is None:
            protected_keys = set()

        if existing_entry:
            # TODO: Use _update_existing_entry like other classes
            dumped = self.model_dump(exclude=protected_keys)
            # If no values are changed modified_at will not be autoamtically set,
            # the easy way to fix this is to just set it manually so there will
            # always be a changed value.
            dumped["modified_at"] = tz_datetime.now()
            return existing_entry.sqlmodel_update(dumped)

        entry = ChannelShow.model_validate(self, update={"channel_id": channel.id})
        channel.shows.append(entry)
        return entry


class SortKeyInput(BaseModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    _SPECIAL_FIELDS = frozenset(
        {
            "random",
            "recently_aired",
            "last_watched",
            "episode_count",
            "started",
        },
    )
    _MODEL_MAP: dict[str, type[Episode | Season | Show | Source | Plugin]] = {
        "episode": Episode,
        "season": Season,
        "show": Show,
        "source": Source,
        "plugin": Plugin,
    }

    model: Literal["episode", "season", "show", "source", "plugin"]
    field: str
    direction: Literal["ascending", "descending"]
    mode: Literal["normal", "interleave_sequential", "interleave_random", "show_group"]
    aggregation: Literal["sum", "count", "max", "min", "first_value", "avg"] | None = (
        None
    )
    days: int | None = None
    recently_aired_date: datetime | None = PydanticField(
        default=None,
        validation_alias="recentlyAiredDate",
        serialization_alias="recentlyAiredDate",
    )

    @property
    def model_class(self) -> type[Episode | Season | Show | Source | Plugin]:
        return self._MODEL_MAP[self.model]

    @model_validator(mode="after")
    def validate_and_resolve(self) -> SortKeyInput:
        if self.field in self._SPECIAL_FIELDS:
            return self

        if self.field not in self.model_class.model_fields:
            msg = f"Invalid field '{self.field}' for model '{self.model}'"
            raise ValueError(msg)
        return self


def parse_sort_key_input(v: Any) -> Any:
    if isinstance(v, str):
        return json.loads(v)
    return v


class ChannelMediaFilter(SQLModel):
    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)

    sort_by: list[Annotated[SortKeyInput, BeforeValidator(parse_sort_key_input)]] = (
        PydanticField(
            default=[],
            validation_alias="sortBy",
            serialization_alias="sortBy",
        )
    )

    additional_channels: list[uuid.UUID] = PydanticField(
        default=[],
        validation_alias="additionalChannels",
        serialization_alias="additionalChannels",
    )
    random_seed: int = PydanticField(
        default=42,
        validation_alias="randomSeed",
        serialization_alias="randomSeed",
    )
    hide_watched: bool = PydanticField(
        default=False,
        validation_alias="hideWatched",
        serialization_alias="hideWatched",
    )
    hide_unwatched: bool = PydanticField(
        default=False,
        validation_alias="hideUnwatched",
        serialization_alias="hideUnwatched",
    )
    # Absolute date filters (ISO date strings)
    maximum_watch_date_absolute: datetime | None = PydanticField(
        default=None,
        validation_alias="maximumWatchDateAbsolute",
        serialization_alias="maximumWatchDateAbsolute",
    )
    minimum_air_date_absolute: datetime | None = PydanticField(
        default=None,
        validation_alias="minimumAirDateAbsolute",
        serialization_alias="minimumAirDateAbsolute",
    )
    maximum_air_date_absolute: datetime | None = PydanticField(
        default=None,
        validation_alias="maximumAirDateAbsolute",
        serialization_alias="maximumAirDateAbsolute",
    )
    minimum_release_date_absolute: datetime | None = PydanticField(
        default=None,
        validation_alias="minimumReleaseDateAbsolute",
        serialization_alias="minimumReleaseDateAbsolute",
    )
    maximum_release_date_absolute: datetime | None = PydanticField(
        default=None,
        validation_alias="maximumReleaseDateAbsolute",
        serialization_alias="maximumReleaseDateAbsolute",
    )

    # Relative date filters (integer days ago)
    maximum_watch_date_relative: int | None = PydanticField(
        default=None,
        validation_alias="maximumWatchDateRelative",
        serialization_alias="maximumWatchDateRelative",
    )
    minimum_air_date_relative: int | None = PydanticField(
        default=None,
        validation_alias="minimumAirDateRelative",
        serialization_alias="minimumAirDateRelative",
    )
    maximum_air_date_relative: int | None = PydanticField(
        default=None,
        validation_alias="maximumAirDateRelative",
        serialization_alias="maximumAirDateRelative",
    )
    minimum_release_date_relative: int | None = PydanticField(
        default=None,
        validation_alias="minimumReleaseDateRelative",
        serialization_alias="minimumReleaseDateRelative",
    )
    maximum_release_date_relative: int | None = PydanticField(
        default=None,
        validation_alias="maximumReleaseDateRelative",
        serialization_alias="maximumReleaseDateRelative",
    )

    only_started_shows: bool = PydanticField(
        default=False,
        validation_alias="onlyStartedShows",
        serialization_alias="onlyStartedShows",
    )
    only_new_shows: bool = PydanticField(
        default=False,
        validation_alias="onlyNewShows",
        serialization_alias="onlyNewShows",
    )
    minimum_duration: int | None = PydanticField(
        default=None,
        validation_alias="minimumDuration",
        serialization_alias="minimumDuration",
    )
    maximum_duration: int | None = PydanticField(
        default=None,
        validation_alias="maximumDuration",
        serialization_alias="maximumDuration",
    )
    limit: int | None = PydanticField(
        default=None,
        ge=1,
    )


class EpisodeWithExtrasOutput(EpisodeOutput):
    watch_date: datetime | None = None
    verified: bool | None = None
    episode_watch_id: uuid.UUID | None = Field(default=None)
    channel_id: uuid.UUID


# This class uses no default values so when initialized blank lists and dicts need to be
# supplied, this is a workaround because using default_factory, default, or "= {}" will
# make the FastAPI endpoint list those fields as optional.
class ChannelEpisodesOutput(SQLModel):
    # The order of episodes matters so it must be a list, everything else can be a dict
    # because the order does not matter.
    episodes: list[EpisodeWithExtrasOutput]
    seasons: dict[uuid.UUID, SeasonOutput]
    shows: dict[uuid.UUID, ShowOutput]
    sources: dict[uuid.UUID, SourceOutput]
    plugins: dict[uuid.UUID, PluginOutput]
    channels: dict[uuid.UUID, ChannelOutput]


class ChannelShowsOutput(SQLModel):
    shows: list[ShowOutput] = Field(default_factory=list)
    sources: dict[uuid.UUID, SourceOutput] = Field(default_factory=dict)


class WhitelistEntryInput(SQLModel):
    id: uuid.UUID
    enabled: bool


class WhitelistShowInput(SQLModel):
    whitelist_mode: bool | None = None
    seasons: list[WhitelistEntryInput] = []
    episodes: list[WhitelistEntryInput] = []


class WhitelistShowOutput(ShowOutput):
    whitelist_mode: bool
    enabled_season_ids: list[uuid.UUID]
    enabled_episode_ids: list[uuid.UUID]
    seasons: list[SeasonOutput]
    episodes: list[EpisodeOutput]


class SortOptionOutput(BaseModel):
    label: str
    model: Literal["episode", "season", "show", "source", "plugin"]
    field: str


class MultipleSortOptionOutputs(BaseModel):
    data: list[SortOptionOutput]
