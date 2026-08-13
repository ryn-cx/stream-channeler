# TODO: Validate
"""Channel models."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, ClassVar, override

from sqlalchemy import util
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
)

from app.episodes.models import Episode
from app.models import (
    DateTimeField,
    RootRecordMixin,
    TimestampIdAndHashMixin,
    Visibility,
)
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.comments.models import Comment


# TODO: Validate
def _canonical_show_id(show: Show | uuid.UUID) -> uuid.UUID | None:
    """Return the id of the title `show` is a copy of."""
    return show.canonical_show_id if isinstance(show, Show) else show


# TODO: Validate
class BaseChannel(SQLModel):
    """Base model representing a Channel."""

    name: str | None = Field(default=None)
    channel_number: float | None = Field(default=None)
    visibility: Visibility = Field()
    default_order: str | None = Field(default=None)
    description: str | None = Field(default=None)
    anonymous: bool = Field()


# TODO: Validate
class BaseAdminChannel(BaseChannel):
    """Base model representing a `Channel` as an admin sees it."""

    score: int = Field(default=0)
    user_id: uuid.UUID


# TODO: Validate
class Channel(BaseAdminChannel, TimestampIdAndHashMixin, RootRecordMixin, table=True):
    """Model representing a Channel."""

    # An episode is sorted by the channel it was added through rather than by
    # anything stored on the channel itself, so its id is all there is to sort on.
    SORTABLE_FIELDS: ClassVar[list[str]] = ["id"]

    __table_args__ = (
        # Used to lookup a channel by its id.
        PrimaryKeyConstraint("id"),
        # Used to list all channels owned by a user.
        Index("Channel-user_id-index", "user_id"),
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="channels")

    shows: list[ChannelShow] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )
    queue: list[ChannelQueue] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )
    episode_orders: list[ChannelSavedEpisodeOrder] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )
    combined_channels: list[ChannelCombinedChannel] = Relationship(
        back_populates="channel",
        cascade_delete=True,
        sa_relationship_kwargs={
            "foreign_keys": "ChannelCombinedChannel.channel_id",
        },
    )
    favorites: list[ChannelFavorite] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )
    comments: list[Comment] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )

    # TODO: Validate
    @property
    def parent(self) -> User:
        """Return the `User` that owns this `Channel`."""
        return self.user

    # TODO: Validate
    @override
    def _root_record(self, session: Session) -> Channel:
        return self


# TODO: Validate
class BaseChannelShow(SQLModel):
    """Base model representing the media that belongs to a `Channel`."""

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    canonical_show_id: uuid.UUID = Field(
        foreign_key="show.id",
        ondelete="CASCADE",
    )
    """The title this row is about, rather than one website's copy of it. Every
    `Show` that is a copy of it belongs to the `Channel`, which is what lets a
    filter set on one website's copy cover the same media everywhere."""
    is_whitelist: bool = Field()
    """If true any entries in the `ChannelSourceFilter`, `ChannelEpisodeFilter` and
    `ChannelSeasonFilter` tables are treated as a whitelist entries so shows, episodes
    and seasons will only be included if they are in the tables. If false any entries in
    the `ChannelSourceFilter`, `ChannelEpisodeFilter` and `ChannelSeasonFilter` tables
    are treated as a blacklist so shows, episodes and seasons will be excluded if they
    are in the tables."""
    is_blacklist_only: bool = Field()
    """If true this `ChannelShow` is only used to filter out episodes and seasons."""


# TODO: Validate
class ChannelShow(BaseChannelShow, TimestampIdAndHashMixin, table=True):
    """Model representing the media that belongs to a `Channel`."""

    __table_args__ = (
        # Used to ensure each title is unique within a channel.
        # Used by cascade deletions when a channel is deleted.
        PrimaryKeyConstraint("channel_id", "canonical_show_id"),
        # Used to find every channel a title belongs to.
        Index("ChannelShow-canonical_show_id-index", "canonical_show_id"),
    )

    channel: Channel = Relationship(back_populates="shows")

    source_filters: list[ChannelSourceFilter] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )
    season_filters: list[ChannelSeasonFilter] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )
    episode_filters: list[ChannelEpisodeFilter] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )

    # TODO: Validate
    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel: Channel,
        show: Show | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelShow | None:
        """Get the `ChannelShow` if it exists.

        This is a wrapper around `db.get`. `show` is either a `Show`, whose
        canonical title is read off it, or that title's id itself.

        Returns:
            The matching `ChannelShow` if found, else `None`.

        """
        return session.get(
            cls,
            (channel.id, _canonical_show_id(show)),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    # TODO: Validate
    @classmethod
    def get_one(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel: Channel,
        show: Show | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelShow:
        """Get the `ChannelShow`, raising if not found.

        This is a wrapper around `db.get_one`. `show` is either a `Show`, whose
        canonical title is read off it, or that title's id itself.

        Returns:
            The matching `ChannelShow`.

        Raises:
            NoResultFound: If no `ChannelShow` links the given channel and title.

        """
        return session.get_one(
            cls,
            (channel.id, _canonical_show_id(show)),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


# TODO: Validate
class BaseChannelSourceFilter(SQLModel):
    """Base model representing the `Show`s that are filtered for a `ChannelShow`."""

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")


# TODO: Validate
class ChannelSourceFilter(BaseChannelSourceFilter, TimestampIdAndHashMixin, table=True):
    """Model representing the `Show`s that are filtered for a `ChannelShow`.

    A `ChannelShow` is a title rather than one website's copy of it, so this is
    where a `User` says which websites' copies of it they want.
    """

    __table_args__ = (
        # Used to ensure each Show is unique within a ChannelShow.
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "show_id"),
        # Used to cascade deletions when a show is deleted.
        Index("ChannelSourceFilter-show_id-index", "show_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="source_filters")
    show: Show = Relationship(back_populates="channel_filters")

    # TODO: Validate
    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel_show: ChannelShow,
        show: Show | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelSourceFilter | None:
        """Get the `ChannelSourceFilter` if it exists.

        This is a wrapper around `db.get`.

        Returns:
            The matching `ChannelSourceFilter` if found, else `None`.

        """
        show_id = show.id if isinstance(show, Show) else show
        return session.get(
            cls,
            (channel_show.id, show_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


# TODO: Validate
class BaseChannelSeasonFilter(SQLModel):
    """Base model representing the seasons that are filtered for a `ChannelShow`."""

    canonical_season_id: uuid.UUID = Field(
        foreign_key="season.id",
        ondelete="CASCADE",
    )
    """The season this row is about, rather than one website's copy of it, so the
    filter covers the same season on every website the title is on."""


# TODO: Validate
class ChannelSeasonFilter(BaseChannelSeasonFilter, TimestampIdAndHashMixin, table=True):
    """Model representing the seasons that are filtered for a `ChannelShow`."""

    __table_args__ = (
        # Used to ensure each season is unique within a ChannelShow.
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "canonical_season_id"),
        # Used to find every channel show filtering a season.
        Index("ChannelSeasonFilter-canonical_season_id-index", "canonical_season_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="season_filters")

    # TODO: Validate
    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel_show: ChannelShow,
        season: Season | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelSeasonFilter | None:
        """Get the `ChannelSeasonFilter` if it exists.

        This is a wrapper around `db.get`. `season` is either a `Season`, whose
        canonical season is read off it, or that season's id itself.

        Returns:
            The matching `ChannelSeasonFilter` if found, else `None`.

        """
        canonical_id = (
            season.canonical_season_id if isinstance(season, Season) else season
        )
        return session.get(
            cls,
            (channel_show.id, canonical_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


# TODO: Validate
class BaseChannelEpisodeFilter(SQLModel):
    """Base model representing the episodes that are filtered for a `ChannelShow`."""

    canonical_episode_id: uuid.UUID = Field(
        foreign_key="episode.id",
        ondelete="CASCADE",
    )
    """The episode this row is about, rather than one website's copy of it, so the
    filter covers the same episode on every website the title is on."""
    # When the filter stops applying. `None` means it never expires. Once `expires_at`
    # is in the past the entry is ignored (a blacklist stops hiding the episode, a
    # whitelist stops including it).
    expires_at: datetime | None = DateTimeField(default=None)


# TODO: Validate
class ChannelEpisodeFilter(
    BaseChannelEpisodeFilter,
    TimestampIdAndHashMixin,
    table=True,
):
    """Model representing the episodes that are filtered for a `ChannelShow`."""

    __table_args__ = (
        # Used to ensure each episode is unique within a ChannelShow.
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "canonical_episode_id"),
        # Used to find every channel show filtering an episode.
        Index(
            "ChannelEpisodeFilter-canonical_episode_id-index",
            "canonical_episode_id",
        ),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="episode_filters")

    # TODO: Validate
    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel_show: ChannelShow,
        episode: Episode | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelEpisodeFilter | None:
        """Get the ChannelEpisodeFilter if it exists.

        This is a wrapper around `db.get`. `episode` is either an `Episode`, whose
        canonical episode is read off it, or that episode's id itself.

        Returns:
            The matching ChannelEpisodeFilter if found, else None.

        """
        canonical_id = (
            episode.canonical_episode_id if isinstance(episode, Episode) else episode
        )
        return session.get(
            cls,
            (channel_show.id, canonical_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


# TODO: Validate
class URLStatus(Enum):
    """Enum representing the status of a URL in the channel queue."""

    PENDING = "Pending"
    FAILED = "Failed"
    IMPORTED = "Imported"
    IMPORTING = "Importing"


# TODO: Validate
class BaseChannelQueue(SQLModel):
    """Base model representing a URL in a channel's import queue."""

    url: str = Field()
    status: URLStatus = Field()
    note: str | None = Field(default=None)
    # The earliest time the URL may be imported. Set by a plugin that wants the
    # import retried later, such as after its API's daily quota runs out.
    import_at: datetime | None = DateTimeField(default=None)


# TODO: Validate
class ChannelQueue(BaseChannelQueue, TimestampIdAndHashMixin, table=True):
    """Model representing a URL in a channel's import queue."""

    # Used to lookup the queue for a specific channel.
    __table_args__ = (PrimaryKeyConstraint("channel_id", "url"),)

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(back_populates="queue")


# TODO: Validate
class BaseChannelSavedEpisodeOrder(SQLModel):
    # Position of the episode in the channel's saved order (0-indexed). Episodes
    # without a row are appended to the end ordered by their creation time.
    position: int = Field()


# TODO: Validate
class ChannelSavedEpisodeOrder(
    BaseChannelSavedEpisodeOrder,
    TimestampIdAndHashMixin,
    table=True,
):
    __table_args__ = (
        PrimaryKeyConstraint("channel_id", "canonical_episode_id"),
        Index(
            "ChannelSavedEpisodeOrder-channel_id-position-index",
            "channel_id",
            "position",
        ),
        Index(
            "ChannelSavedEpisodeOrder-canonical_episode_id-index",
            "canonical_episode_id",
        ),
    )

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(back_populates="episode_orders")

    # The episode itself, so a saved position survives the copy it was saved
    # against being deleted and covers every copy of that episode.
    canonical_episode_id: uuid.UUID = Field(
        foreign_key="episode.id",
        ondelete="CASCADE",
    )


# TODO: Validate
class ChannelCombinedChannel(TimestampIdAndHashMixin, table=True):
    """Model representing the additional `Channel`s combined into a `Channel`."""

    __table_args__ = (
        # Each combined channel is unique within a channel; the leading column also
        # serves lookups of a channel's combined channels and cascade deletion when
        # the owning channel is deleted.
        PrimaryKeyConstraint("channel_id", "combined_channel_id"),
        # Used by cascade deletion when a combined channel is deleted.
        Index(
            "ChannelCombinedChannel-combined_channel_id-index",
            "combined_channel_id",
        ),
    )

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    combined_channel_id: uuid.UUID = Field(
        foreign_key="channel.id",
        ondelete="CASCADE",
    )
    channel: Channel = Relationship(
        back_populates="combined_channels",
        sa_relationship_kwargs={
            "foreign_keys": "ChannelCombinedChannel.channel_id",
        },
    )


# TODO: Validate
class ChannelFavorite(TimestampIdAndHashMixin, table=True):
    """Model representing a `Channel` a `User` has favorited."""

    __table_args__ = (
        # Each channel is favorited at most once per user; the leading column also
        # serves lookups of a user's favorites.
        PrimaryKeyConstraint("user_id", "channel_id"),
        # Used by cascade deletion when a channel is deleted.
        Index("ChannelFavorite-channel_id-index", "channel_id"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="favorite_channels")

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(back_populates="favorites")

    # The `User`'s private overrides for how this favorited `Channel` is shown to
    # them. Each is `None` when the user hasn't customized it and the shared
    # `Channel` value is used instead.
    name: str | None = Field(default=None)
    channel_number: float | None = Field(default=None)

    # TODO: Validate
    @property
    def parent(self) -> Channel:
        """Return the `Channel` that was favorited."""
        return self.channel

    # TODO: Validate
    def owner_id(self, _session: Session) -> uuid.UUID:
        """Return the `id` of the `User` who favorited the `Channel`."""
        return self.user_id

    # TODO: Validate
    def is_publically_readable(self, _session: Session) -> bool:
        """Return false because a favorite is only ever readable by its `User`."""
        return False
