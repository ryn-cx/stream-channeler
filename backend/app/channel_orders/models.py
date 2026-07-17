"""Channel order models."""

import uuid
from typing import override

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

    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    visibility: Visibility = Field()
    anonymous: bool = Field(default=False)
    config: str = Field()
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

    @property
    def parent(self) -> User:
        """Return the `User` that owns this `ChannelOrder`."""
        return self.user

    @override
    def _root_record(self, session: Session) -> ChannelOrder:
        return self
