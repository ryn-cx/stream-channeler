import uuid
from collections.abc import Sequence
from enum import Enum
from typing import TYPE_CHECKING, Any

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
from app.models import TimestampIdAndHashMixin
from app.seasons.models import Season
from app.shows.models import Show
from app.users.models import User

if TYPE_CHECKING:
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter


class BaseChannel(SQLModel):
    name: str | None = Field(default=None)
    channel_number: float | None = Field(default=None)
    public: bool = Field(default=False)
    default_order: str | None = Field(default=None)


class Channel(BaseChannel, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
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

    @property
    def parent(self) -> User:
        """Return the user that owns this channel."""
        return self.user

    def get_user_id(self, _session: Session) -> uuid.UUID:
        """Return the id of the user that owns this channel."""
        return self.user_id

    def is_public(self, _session: Session) -> bool:
        """Return whether this channel is publicly accessible."""
        return self.public


class BaseChannelShow(SQLModel):
    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    white_list_mode: bool = Field()


class ChannelShow(BaseChannelShow, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        # Used in _filter_episodes_by_channels to filter episodes by channel.
        PrimaryKeyConstraint("channel_id", "show_id"),
        # Used to cascade deletions when a show is deleted.
        Index("ChannelShow-show_id-index", "show_id"),
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
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        db: Session,
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
        """Get the ChannelShow if it exists.

        This is a wrapper around ``db.get``.

        Returns:
            The matching ChannelShow if found, else None.

        """
        show_id = show.id if isinstance(show, Show) else show
        return db.get(
            cls,
            (channel.id, show_id),
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
        db: Session,
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
        """Get the ChannelShow, raising if not found.

        This is a wrapper around ``db.get_one``.

        Returns:
            The matching ChannelShow.

        Raises:
            NoResultFound: If no ChannelShow links the given channel and show.

        """
        show_id = show.id if isinstance(show, Show) else show
        return db.get_one(
            cls,
            (channel.id, show_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


class BaseChannelSeasonWhiteList(SQLModel):
    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")


class ChannelSeasonWhiteList(
    BaseChannelSeasonWhiteList,
    TimestampIdAndHashMixin,
    table=True,
):
    __table_args__ = (
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "season_id"),
        # Used to cascade deletions when a season is deleted.
        Index("ChannelSeasonWhiteList-season_id-index", "season_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="season_white_list")
    season: Season = Relationship(back_populates="channel_white_list")

    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        db: Session,
        channel_show: ChannelShow,
        season: Season | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelSeasonWhiteList | None:
        """Get the ChannelSeasonWhiteList if it exists.

        This is a wrapper around ``db.get``.

        Returns:
            The matching ChannelSeasonWhiteList if found, else None.

        """
        season_id = season.id if isinstance(season, Season) else season
        return db.get(
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
        db: Session,
        channel_show: ChannelShow,
        season: Season | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelSeasonWhiteList:
        """Get the ChannelSeasonWhiteList, raising if not found.

        This is a wrapper around ``db.get_one``.

        Returns:
            The matching ChannelSeasonWhiteList.

        Raises:
            NoResultFound: If no ChannelSeasonWhiteList links the given channel show
                and season.

        """
        season_id = season.id if isinstance(season, Season) else season
        return db.get_one(
            cls,
            (channel_show.id, season_id),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )


class BaseChannelEpisodeWhiteList(SQLModel):
    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")


class ChannelEpisodeWhiteList(
    BaseChannelEpisodeWhiteList,
    TimestampIdAndHashMixin,
    table=True,
):
    __table_args__ = (
        # Used to cascade deletions when a channel show is deleted.
        PrimaryKeyConstraint("channel_show_id", "episode_id"),
        # Used to cascade deletions when an episode is deleted.
        Index("ChannelEpisodeWhiteList-episode_id-index", "episode_id"),
    )

    channel_show_id: uuid.UUID = Field(foreign_key="channelshow.id", ondelete="CASCADE")
    channel_show: ChannelShow = Relationship(back_populates="episode_white_list")
    episode: Episode = Relationship(back_populates="white_lists")

    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        db: Session,
        channel_show: ChannelShow,
        episode: Episode | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelEpisodeWhiteList | None:
        """Get the ChannelEpisodeWhiteList if it exists.

        This is a wrapper around ``db.get``.

        Returns:
            The matching ChannelEpisodeWhiteList if found, else None.

        """
        episode_id = episode.id if isinstance(episode, Episode) else episode
        return db.get(
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
        db: Session,
        channel_show: ChannelShow,
        episode: Episode | uuid.UUID,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> ChannelEpisodeWhiteList:
        """Get the ChannelEpisodeWhiteList, raising if not found.

        This is a wrapper around ``db.get_one``.

        Returns:
            The matching ChannelEpisodeWhiteList.

        Raises:
            NoResultFound: If no ChannelEpisodeWhiteList links the given channel show
                and episode.

        """
        episode_id = episode.id if isinstance(episode, Episode) else episode
        return db.get_one(
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
    PENDING = "Pending"
    FAILED = "Failed"
    IMPORTED = "Imported"
    IMPORTING = "Importing"


class BaseChannelQueue(SQLModel):
    url: str = Field()
    status: URLStatus = Field()
    note: str | None = Field(default=None)


class ChannelQueue(BaseChannelQueue, TimestampIdAndHashMixin, table=True):
    # Used to lookup the queue for a specific channel.
    __table_args__ = (PrimaryKeyConstraint("channel_id", "url"),)

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(back_populates="queue")
