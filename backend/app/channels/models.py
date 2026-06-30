# TODO: Validate
"""Channel models."""

import uuid
from collections.abc import Sequence
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, override

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


class BaseChannel(SQLModel):
    """Base model representing a Channel."""

    name: str | None = Field(default=None)
    channel_number: float | None = Field(default=None)
    visibility: Visibility = Field()
    default_order: str | None = Field(default=None)
    description: str | None = Field(default=None)
    anonymous: bool = Field(default=False)


class Channel(BaseChannel, TimestampIdAndHashMixin, RootRecordMixin, table=True):
    """Model representing a Channel."""

    __table_args__ = (
        # Used to lookup a channel by its id.
        PrimaryKeyConstraint("id"),
        # Used to list all channels owned by a user.
        Index("Channel-user_id-index", "user_id"),
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="channels")
    score: int = Field(default=0)

    shows: list[ChannelShow] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )
    queue: list[ChannelQueue] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )

    @property
    def parent(self) -> User:
        """Return the `User` that owns this `Channel`."""
        return self.user

    @override
    def _root_record(self, session: Session) -> Channel:
        return self


class BaseChannelShow(SQLModel):
    """Base model representing the `Shows` that belong to a `Channel`."""

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    is_whitelist: bool = Field()
    """If true any entries in the `ChannelEpisodeFilter` and `ChannelSeasonFilter`
    tables are treated as a whitelist entries so episodes and seasons will only be
    included if they are in the tables. If false any entries in the
    `ChannelEpisodeFilter` and `ChannelSeasonFilter` tables are treated as a blacklist
    so episodes and seasons will be excluded if they are in the tables."""
    is_blacklist_only: bool = Field()
    """If true this `ChannelShow` is only used to filter out episodes and seasons."""


class ChannelShow(BaseChannelShow, TimestampIdAndHashMixin, table=True):
    """Model representing the `Shows` that belong to a `Channel`."""

    __table_args__ = (
        # Used to ensure each show is unique within a channel.
        # Used by cascade deletions when a channel is deleted.
        PrimaryKeyConstraint("channel_id", "show_id"),
        # Used by cascade deletions when a show is deleted.
        Index("ChannelShow-show_id-index", "show_id"),
    )

    channel: Channel = Relationship(back_populates="shows")
    show: Show = Relationship(back_populates="channels")

    season_filters: list[ChannelSeasonFilter] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )
    episode_filters: list[ChannelEpisodeFilter] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )

    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel: Channel,
        show: Show,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelShow | None:
        """Get the `ChannelShow` if it exists.

        This is a wrapper around `db.get`.

        Returns:
            The matching `ChannelShow` if found, else `None`.

        """
        return session.get(
            cls,
            (channel.id, show.id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_one(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        channel: Channel,
        show: Show,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelShow:
        """Get the `ChannelShow`, raising if not found.

        This is a wrapper around `db.get_one`.

        Returns:
            The matching `ChannelShow`.

        Raises:
            NoResultFound: If no `ChannelShow` links the given channel and show.

        """
        return session.get_one(
            cls,
            (channel.id, show.id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


class BaseChannelSeasonFilter(SQLModel):
    """Base model representing the `Seasons` that are filtered for a `ChannelShow`."""

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")


class ChannelSeasonFilter(BaseChannelSeasonFilter, TimestampIdAndHashMixin, table=True):
    """Model representing the `Seasons` that are filtered for a `ChannelShow`."""

    __table_args__ = (
        # Used to ensure each Season is unique within a ChannelShow.
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "season_id"),
        # Used to cascade deletions when a season is deleted.
        Index("ChannelSeasonFilter-season_id-index", "season_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="season_filters")
    season: Season = Relationship(back_populates="channel_filters")

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

        This is a wrapper around `db.get`.

        Returns:
            The matching `ChannelSeasonFilter` if found, else `None`.

        """
        season_id = season.id if isinstance(season, Season) else season
        return session.get(
            cls,
            (channel_show.id, season_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_one(  # noqa: PLR0913 - Copied from wrapped function
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
    ) -> ChannelSeasonFilter:
        """Get the `ChannelSeasonFilter`, raising if not found.

        This is a wrapper around `db.get_one`.

        Returns:
            The matching `ChannelSeasonFilter`.

        Raises:
            NoResultFound: If no `ChannelSeasonFilter` links the given `ChannelShow`
                and `Season`.

        """
        season_id = season.id if isinstance(season, Season) else season
        return session.get_one(
            cls,
            (channel_show.id, season_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


class BaseChannelEpisodeFilter(SQLModel):
    """Base model representing the `Episodes` that are filtered for a `ChannelShow`."""

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    # When the filter stops applying. `None` means it never expires. Once `expires_at`
    # is in the past the entry is ignored (a blacklist stops hiding the episode, a
    # whitelist stops including it).
    expires_at: datetime | None = DateTimeField(default=None)


class ChannelEpisodeFilter(
    BaseChannelEpisodeFilter,
    TimestampIdAndHashMixin,
    table=True,
):
    """Model representing the `Episodes` that are filtered for a `ChannelShow`."""

    __table_args__ = (
        # Used to ensure each Episode is unique within a ChannelShow.
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "episode_id"),
        # Used to cascade deletions when an episode is deleted.
        Index("ChannelEpisodeFilter-episode_id-index", "episode_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="episode_filters")
    episode: Episode = Relationship(back_populates="channel_filters")

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

        This is a wrapper around `db.get`.

        Returns:
            The matching ChannelEpisodeFilter if found, else None.

        """
        episode_id = episode.id if isinstance(episode, Episode) else episode
        return session.get(
            cls,
            (channel_show.id, episode_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    @classmethod
    def get_one(  # noqa: PLR0913 - Copied from wrapped function
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
    ) -> ChannelEpisodeFilter:
        """Get the `ChannelEpisodeFilter`, raising if not found.

        This is a wrapper around `db.get_one`.

        Returns:
            The matching `ChannelEpisodeFilter`.

        Raises:
            NoResultFound: If no `ChannelEpisodeFilter` links the given `ChannelShow`
                and `Episode`.

        """
        episode_id = episode.id if isinstance(episode, Episode) else episode
        return session.get_one(
            cls,
            (channel_show.id, episode_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


class URLStatus(Enum):
    """Enum representing the status of a URL in the channel queue."""

    PENDING = "Pending"
    FAILED = "Failed"
    IMPORTED = "Imported"
    IMPORTING = "Importing"


class BaseChannelQueue(SQLModel):
    """Base model representing a URL in a channel's import queue."""

    url: str = Field()
    status: URLStatus = Field()
    note: str | None = Field(default=None)


class ChannelQueue(BaseChannelQueue, TimestampIdAndHashMixin, table=True):
    """Model representing a URL in a channel's import queue."""

    # Used to lookup the queue for a specific channel.
    __table_args__ = (PrimaryKeyConstraint("channel_id", "url"),)

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(back_populates="queue")
