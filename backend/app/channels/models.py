# TODO: Validate
import uuid
from enum import Enum
from typing import Self

from sqlalchemy import ScalarResult
from sqlalchemy.sql.base import ExecutableOption
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
    select,
)

from app.media.models import Episode, Season, Show
from app.models import TimestampIdMixin
from app.users.models import User


class BaseChannel(SQLModel):
    name: str = Field()
    public: bool = Field(default=False)
    # Default value is required to be able to create a channel without a default order.
    # TODO: Make this always a str
    default_order: str | None = Field(default=None)


class Channel(BaseChannel, TimestampIdMixin, table=True):
    __table_args__ = (PrimaryKeyConstraint("user_id", "name"),)

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(
        back_populates="channels",
    )

    shows: list[ChannelShow] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )
    queue: list[ChannelQueue] = Relationship(
        back_populates="channel",
        cascade_delete=True,
    )

    @classmethod
    def get(
        cls,
        db: Session,
        user: User | uuid.UUID,
        name: str,
        options: list[ExecutableOption] | None = None,
    ) -> Channel | None:
        """Get a channel by the parent user and channel name.

        Args:
            db: Database session
            user: Parent user instance
            name: Unique name of the channel within the user
            options: SQLAlchemy query options (e.g., joinedload, selectinload)

        Returns:
            Channel instance if found, None otherwise
        """
        return cls._get_query(db, user, name, options).first()

    @classmethod
    def get_one(
        cls,
        db: Session,
        user: User | uuid.UUID,
        name: str,
        options: list[ExecutableOption] | None = None,
    ) -> Channel:
        """Get a channel by the user and channel name.

        Raises an exception if no match is found.

        Args:
            db: Database session
            user: Parent user instance
            name: Unique name of the channel within the user
            options: SQLAlchemy query options (e.g., joinedload, selectinload)

        Returns:
            Channel instance
        """
        return cls._get_query(db, user, name, options).one()

    @classmethod
    def _get_query(
        cls,
        db: Session,
        user: User | uuid.UUID,
        name: str,
        options: list[ExecutableOption] | None = None,
    ) -> ScalarResult[Self]:
        if isinstance(user, User):
            user = user.id
        statement = (
            select(cls)
            .where(cls.user_id == user, cls.name == name)
            .options(*(options or []))
        )
        return db.exec(statement)


class BaseChannelShow(SQLModel):
    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    white_list_mode: bool = Field()


class ChannelShow(BaseChannelShow, TimestampIdMixin, table=True):
    """Many-to-many relationship between Channels and Shows."""

    __table_args__ = (
        # Used to find all shows in a channel
        Index("ChannelShow-channel_id-index", "channel_id"),
        Index("ChannelShow-show_id-index", "show_id"),
        PrimaryKeyConstraint("channel_id", "show_id"),
    )

    channel: Channel = Relationship(
        back_populates="shows",
    )
    show: Show = Relationship(
        back_populates="channels",
    )

    season_white_list: list[ChannelSeasonWhiteList] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )
    episode_white_list: list[ChannelEpisodeWhiteList] = Relationship(
        back_populates="channel_show",
        cascade_delete=True,
    )

    @classmethod
    def get(
        cls,
        db: Session,
        channel: Channel,
        show: Show | uuid.UUID,
        options: list[ExecutableOption] | None = None,
    ) -> ChannelShow | None:
        """Get a channel by the parent user and channel name.

        Args:
            db: Database session
            channel: Parent channel instance
            show: Parent show instance or its key
            options: SQLAlchemy query options (e.g., joinedload, selectinload)

        Returns:
            Channel instance if found, None otherwise
        """
        return cls._get_query(db, channel, show, options).first()

    @classmethod
    def get_one(
        cls,
        db: Session,
        channel: Channel,
        show: Show | uuid.UUID,
        options: list[ExecutableOption] | None = None,
    ) -> ChannelShow:
        """Get a channel by the user and channel name.

        Raises an exception if no match is found.

        Args:
            db: Database session
            channel: Parent channel instance
            show: Parent show instance or its key
            options: SQLAlchemy query options (e.g., joinedload, selectinload)

        Returns:
            Channel instance
        """
        return cls._get_query(db, channel, show, options).one()

    @classmethod
    def _get_query(
        cls,
        db: Session,
        channel: Channel,
        show: Show | uuid.UUID,
        options: list[ExecutableOption] | None = None,
    ) -> ScalarResult[Self]:
        if isinstance(show, Show):
            show = show.id
        statement = (
            select(cls)
            .where(cls.channel == channel, cls.show_id == show)
            .options(*(options or []))
        )
        return db.exec(statement)


class BaseChannelSeasonWhiteList(SQLModel):
    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")


class ChannelSeasonWhiteList(BaseChannelSeasonWhiteList, TimestampIdMixin, table=True):
    """Many-to-many relationship between Channel Shows and Seasons.

    Allows the user to specify which seasons of a show to include in the channel.
    """

    __table_args__ = (
        # Used to find all seasons in a channel show
        Index("ChannelSeasonWhiteList-channel_show_id-index", "channel_show_id"),
        Index("ChannelSeasonWhiteList-season_id-index", "season_id"),
        PrimaryKeyConstraint("channel_show_id", "season_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(
        back_populates="season_white_list",
    )
    season: Season = Relationship(
        back_populates="channel_white_list",
    )


class BaseChannelEpisodeWhiteList(SQLModel):
    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")


class ChannelEpisodeWhiteList(
    BaseChannelEpisodeWhiteList,
    TimestampIdMixin,
    table=True,
):
    """Many-to-many relationship between Channel Shows and Episodes.

    Allows the user to specify which episodes of a season to include in the channel.
    """

    __table_args__ = (
        # Used to find all episodes in a channel show
        Index("ChannelEpisodeWhiteList-channel_show_id-index", "channel_show_id"),
        Index("ChannelEpisodeWhiteList-episode_id-index", "episode_id"),
        PrimaryKeyConstraint("channel_show_id", "episode_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(
        back_populates="episode_white_list",
    )
    episode: Episode = Relationship(
        back_populates="channel_white_list",
    )


class URLStatus(Enum):
    PENDING = "Pending"
    FAILED = "Failed"
    IMPORTED = "Imported"
    IMPORTING = "Importing"


class BaseChannelQueue(SQLModel):
    url: str = Field()
    status: URLStatus = Field()
    note: str | None = Field(default=None)


class ChannelQueue(BaseChannelQueue, TimestampIdMixin, table=True):
    __table_args__ = (PrimaryKeyConstraint("channel_id", "url"),)

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(
        back_populates="queue",
    )
