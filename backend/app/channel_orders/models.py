# TODO: Validate
"""Channel order models."""

import uuid
from typing import Literal, override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
)

from app.models import (
    RootRecordMixin,
    TimestampIdAndHashMixin,
    Visibility,
)
from app.users.models import User


class BaseChannelOrder(SQLModel):
    """Base model representing a channel order."""

    config: str = Field()
    visibility: Visibility = Field()
    anonymous: bool = Field()
    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    icon: str | None = Field(default=None, max_length=32)


class ChannelOrder(
    BaseChannelOrder,
    TimestampIdAndHashMixin,
    RootRecordMixin,
    table=True,
):
    """Model representing a channel order."""

    __table_args__ = (
        # Used to lookup a channel order by its id.
        PrimaryKeyConstraint("id"),
        # Used to list all channel orders owned by a user.
        Index("ChannelOrder-user_id-index", "user_id"),
    )
    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="channel_orders")
    score: int = Field(default=0)

    favorites: list[ChannelOrderFavorite] = Relationship(
        back_populates="channel_order",
        cascade_delete=True,
    )

    @property
    def parent(self) -> User:
        """Return the `User` that owns this `ChannelOrder`."""
        return self.user

    @override
    def _root_record(self, session: Session) -> ChannelOrder:
        return self


class ChannelOrderFavorite(TimestampIdAndHashMixin, table=True):
    """Model representing a `ChannelOrder` a `User` has favorited."""

    __table_args__ = (
        # Used as a unique constraint.
        PrimaryKeyConstraint("user_id", "channel_order_id"),
        # Used when a ChannelOrder is deleted.
        Index("ChannelOrderFavorite-channel_order_id-index", "channel_order_id"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="favorite_channel_orders")

    channel_order_id: uuid.UUID = Field(
        foreign_key="channelorder.id",
        ondelete="CASCADE",
    )
    channel_order: ChannelOrder = Relationship(back_populates="favorites")

    @property
    def parent(self) -> ChannelOrder:
        """Return the `ChannelOrder` that was favorited."""
        return self.channel_order

    def owner_id(self, _session: Session) -> uuid.UUID:
        return self.user_id

    def is_publically_readable(self, _session: Session) -> Literal[False]:
        return False
