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
    BaseAdminChannel,
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


# TODO: Validate
class ChannelCreate(BaseInput, BaseChannel):
    """Schema for creating a `Channel`."""


# TODO: Validate
class ChannelAdminCreate(BaseInput, BaseAdminChannel):
    """Schema for creating a `Channel` as an admin."""


# TODO: Validate
class ChannelUpdate(
    make_model_with_all_fields_optional(BaseChannel),
    BaseUpdateWithoutKey[Channel],
):
    """Schema for updating a `Channel`."""


# TODO: Validate
class ChannelOutput(BaseChannel):
    """Schema for returning a `Channel`.

    `user_id` and `username` are redacted on anonymous `Channel`s unless the viewer
    owns the record or is an admin.
    """

    id: uuid.UUID
    user_id: uuid.UUID | None
    username: str | None = None
    score: int


# TODO: Validate
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


# TODO: Validate
class ChannelFavoriteUpdate(BaseInput):
    """Schema for a `User`'s private customization of a favorited `Channel`."""

    name: str | None = Field(default=None)
    channel_number: float | None = Field(default=None)


# TODO: Validate
class ChannelPublicListOutput(BaseModel):
    """Schema for returning a page of publicly listed `Channel`s."""

    data: list[ChannelListOutput]
    count: int


# TODO: Validate
class ChannelsPublic(BaseModel):
    """Schema for returning a page of `Channel`s."""

    data: list[ChannelListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class ChannelReadOptions(ScopedReadOptions):
    """Read options for the `Channel` list.

    Defaults to `owned` rather than `ScopedReadOptions`'s `all`, so an unscoped read
    returns the `User`'s own `Channel`s instead of demanding admin rights.
    """

    scope: RecordScope = RecordScope.owned


# TODO: Validate
class ChannelAdminUpdate(
    make_model_with_all_fields_optional(BaseAdminChannel),
    BaseInput,
):
    """Schema for an admin updating any field on a `Channel`.

    Every field an admin creates a `Channel` with can be changed afterwards,
    which includes the `User` it belongs to and its `score`.
    """


# TODO: Validate
class CombinedChannelOutput(BaseModel):
    """Schema for returning a channel combined into another channel."""

    id: uuid.UUID
    name: str | None


# TODO: Validate
class CombinedChannelInput(BaseInput):
    """Schema for combining a channel into another channel."""

    id: uuid.UUID


# TODO: Validate
class ChannelQueueOutput(BaseChannelQueue):
    id: uuid.UUID
    channel_id: uuid.UUID


# TODO: Validate
class ChannelQueueAdminOutput(ChannelQueueOutput):
    """Schema for returning a queue entry to an admin, with channel and owner info."""

    created_at: datetime
    channel_name: str | None
    channel_number: float | None
    user_id: uuid.UUID | None
    username: str | None


# TODO: Validate
class ChannelQueueAdminUpdate(BaseInput):
    """Schema for an admin updating a `Channel`'s queue entry."""

    status: URLStatus | None = Field(default=None)
    note: str | None = Field(default=None)
    import_at: datetime | None = Field(default=None)


# TODO: Validate
class ChannelOrderInput(BaseInput):
    """Schema for setting the custom episode order of a `Channel`."""

    episode_ids: list[uuid.UUID] = Field(default_factory=list)


# TODO: Validate
class EpisodeWithDetails(EpisodeOutput):
    watch_date: datetime | None = Field(default=None)
    verified: bool | None = Field(default=None)
    episode_watch_id: uuid.UUID | None = Field(default=None)
    # The episode's page on themoviedb.org, when it is linked to one.
    tmdb_url: str | None = Field(default=None)
    channel_id: uuid.UUID
    # All in-scope member channels this episode belongs to. The first is `channel_id`
    # (the primary/base channel). Used by the blacklist UI to offer each as a target.
    channel_ids: list[uuid.UUID] = Field(default_factory=list)
    # How TMDB numbers and names the episode and the season it is in, which is not
    # always how the website does. `None` when it is not linked to TMDB.
    tmdb_season_number: int | None = Field(default=None)
    tmdb_season_name: str | None = Field(default=None)
    tmdb_episode_number: int | None = Field(default=None)


# TODO: Validate
class ChannelEpisodesOutput(BaseModel):
    episodes: list[EpisodeWithDetails]
    seasons: dict[uuid.UUID, SeasonOutput]
    shows: dict[uuid.UUID, ShowPublic]
    sources: dict[uuid.UUID, SourcePublic]
    plugins: dict[uuid.UUID, PluginOutput]
    channels: dict[uuid.UUID, ChannelOutput]


# TODO: Validate
class ChannelShowGroup(BaseModel):
    """The regular shows contributed by one channel within a combined channel."""

    channel_id: uuid.UUID
    channel_name: str | None
    shows: list[ShowPublic] = Field(default_factory=list)


# TODO: Validate
class ChannelShowStats(BaseModel):
    """What a channel's rows for one canonical show add up to.

    A canonical show is counted by what its seasons and episodes are rather than by the
    records holding them, so the same season on three websites is one season.
    """

    season_count: int
    episode_count: int


# TODO: Validate
class ChannelShowsOutput(BaseModel):
    shows: list[ShowPublic] = Field(default_factory=list)
    # Shows that don't belong to the channel but carry blacklist/whitelist entries for
    # episodes pulled in from other channels.
    filter_only_shows: list[ShowPublic] = Field(default_factory=list)
    sources: dict[uuid.UUID, SourcePublic] = Field(default_factory=dict)
    # The canonical show behind each row, keyed by `canonical_show_id`. It carries
    # the title's own name, which is what a show is read under rather than the name
    # any one website gave its row for it.
    canonical_shows: dict[uuid.UUID, ShowPublic] = Field(default_factory=dict)
    # The source each canonical show was written by, keyed by `canonical_show_id`.
    # Kept apart from `sources` because that is where a show can be watched and
    # this is who wrote it down, which is never a website carrying it.
    canonical_sources: dict[uuid.UUID, SourcePublic] = Field(default_factory=dict)
    # The regular shows grouped by the channel they come from, with the channel this
    # endpoint was called on first and combined channels after it, sorted by name.
    groups: list[ChannelShowGroup] = Field(default_factory=list)
    # What each canonical show adds up to, keyed by `canonical_show_id` because
    # the stats are about the show rather than one website's row.
    stats: dict[uuid.UUID, ChannelShowStats] = Field(default_factory=dict)


# TODO: Validate
class WhitelistEntryInput(BaseInput):
    id: uuid.UUID
    marked: bool
    # Only meaningful for episode entries; ignored for seasons. `None` = never expires.
    expires_at: datetime | None = Field(default=None)


# TODO: Validate
class BlacklistEpisodeInput(BaseInput):
    show_id: uuid.UUID
    episode_id: uuid.UUID
    expires_at: datetime | None = Field(default=None)


# TODO: Validate
class WhitelistEpisodeSourceEntryInput(BaseInput):
    """An entry naming an episode on one website rather than on all of them."""

    # The website's own row for the episode, whose canonical episode is what the
    # entry ends up naming.
    episode_id: uuid.UUID
    # The website's row for the show, which is what narrows the entry to one site.
    show_id: uuid.UUID
    marked: bool
    # `None` = never expires.
    expires_at: datetime | None = Field(default=None)


# TODO: Validate
class WhitelistShowInput(BaseInput):
    is_whitelist: bool | None = Field(default=None)
    # Each entry's `id` is the `Show` id of one website's row for the show.
    sources: list[WhitelistEntryInput] = Field(default_factory=list)
    seasons: list[WhitelistEntryInput] = Field(default_factory=list)
    episodes: list[WhitelistEntryInput] = Field(default_factory=list)
    episode_sources: list[WhitelistEpisodeSourceEntryInput] = Field(
        default_factory=list,
    )


# TODO: Validate
class WhitelistSourceOutput(BaseModel):
    """One website's row for the show, and whether it is filtered."""

    show_id: uuid.UUID
    source_id: uuid.UUID
    source_name: str | None
    favicon_url: str | None
    # The row itself, so a site carrying the title under more than one row can
    # name each of them, and so one can be edited without being fetched again.
    show: ShowPublic
    filtered: bool
    # TMDB is where the media is catalogued rather than a website it can be
    # watched on, so a row names it for the seasons it has a record of and never
    # for an episode.
    is_tmdb: bool = Field(default=False)


# TODO: Validate
class WhitelistSeasonOutput(SeasonOutput):
    filtered: bool
    # The `Show` ids of the websites' rows that carry this season.
    show_ids: list[uuid.UUID]


# TODO: Validate
class WhitelistEpisodeLinkOutput(EpisodeOutput):
    """One website's row for an episode, and whether it is filtered on its own.

    The row's own columns come with it, since this is the website's account of
    the episode and the one thing an admin editing it edits. `episode_id` names
    the same row as `id` and is kept as what the filters are keyed by.
    """

    show_id: uuid.UUID
    episode_id: uuid.UUID
    # Whether an entry names this episode on this website alone, which is the
    # exception to whatever the season and episode entries decided.
    filtered: bool
    expires_at: datetime | None = Field(default=None)


# TODO: Validate
class WhitelistEpisodeOutput(EpisodeOutput):
    # What a filter names, which is the episode itself where the row is one, so
    # every row served here carries one however it was stored.
    canonical_episode_id: uuid.UUID
    filtered: bool
    expires_at: datetime | None = Field(default=None)
    # The `Show` ids of the websites' rows that carry this episode.
    show_ids: list[uuid.UUID]
    # Each website's row on its own, so one website's account of the episode can
    # be read, and filtered, rather than only the row they were folded into.
    links: list[WhitelistEpisodeLinkOutput]
    # How TMDB numbers and names the episode and the season it is in, which is not
    # always how the website does. `None` when it is not linked to TMDB.
    tmdb_season_number: int | None = Field(default=None)
    tmdb_season_name: str | None = Field(default=None)
    tmdb_episode_number: int | None = Field(default=None)


# TODO: Validate
class WhitelistShowOutput(ShowPublic):
    """The title's sites and seasons, which is what the filter page opens on.

    The episodes are read a season at a time as each is expanded rather than all
    at once, since a title of a thousand episodes is a page nobody waits for and
    all but the one season being looked at is read for nothing.
    """

    is_whitelist: bool
    sources: list[WhitelistSourceOutput]
    seasons: list[WhitelistSeasonOutput]


# TODO: Validate
class WhitelistEpisodesOutput(BaseModel):
    """One page of a season's episodes, and how many the season holds in all."""

    episodes: list[WhitelistEpisodeOutput]
    total_count: int


# TODO: Validate
class SortOptionOutput(BaseModel):
    label: str
    model: Literal["episode", "season", "show", "source", "plugin", "channel"]
    field: str


# TODO: Validate
class SortKeyInput(BaseInput):
    model_config = ConfigDict(
        validate_by_name=True,
        extra="forbid",
        alias_generator=to_camel,
    )  # type: ignore[reportAssignmentType]

    MODEL_MAP: ClassVar[
        dict[
            str,
            type[Episode | Season | Show | Source | Plugin | Channel],
        ]
    ] = {
        "episode": Episode,
        "season": Season,
        "show": Show,
        "source": Source,
        "plugin": Plugin,
        # An episode reads as coming from the channel it was added through, which
        # is a channel of its own rather than one of the media models.
        "channel": Channel,
    }

    model: Literal["episode", "season", "show", "source", "plugin", "channel"]
    field: str
    direction: Literal["ascending", "descending"]
    order: Literal["sequential", "interleave", "randomize"] = Field()
    aggregation: Literal["max", "min", "avg"] | None = Field(default=None)
    days: int | None = Field(default=None)
    recently_aired_date: datetime | None = Field(default=None)
    fuzziness: int | None = Field(default=None, ge=0)

    # TODO: Validate
    @property
    def model_class(
        self,
    ) -> type[Episode | Season | Show | Source | Plugin | Channel]:
        return self.MODEL_MAP[self.model]

    # TODO: Validate
    @model_validator(mode="after")
    def validate_and_resolve(self) -> SortKeyInput:
        if self.field == "random" or self.field in self.model_class.SORTABLE_FIELDS:
            return self

        msg = f"Invalid field '{self.field}' for model '{self.model}'"
        raise ValueError(msg)


# TODO: Validate
class ChannelOptions(BaseInput):
    model_config = ConfigDict(
        validate_by_name=True,
        extra="forbid",
        alias_generator=to_camel,
    )  # type: ignore[reportAssignmentType]

    sort_by: list[SortKeyInput] = Field(default_factory=list)

    # TODO: Validate
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
    maximum_watch_date_relative: int | None = Field(default=None)
    minimum_air_date_relative: int | None = Field(default=None)
    maximum_air_date_relative: int | None = Field(default=None)
    total_shows_count: int | None = Field(default=None, ge=0)
    started_shows_count: int | None = Field(default=None, ge=0)
    new_shows_count: int | None = Field(default=None, ge=0)
    minimum_duration: int | None = Field(default=None)
    maximum_duration: int | None = Field(default=None)
    limit: int | None = Field(default=1000, ge=1, le=1000)
