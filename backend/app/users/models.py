"""User models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, PrimaryKeyConstraint, Relationship, SQLModel

from app.constants import SERVER_SIDE_THRESHOLD_MAXIMUM
from app.models import TimestampIdAndHashMixin
from app.utils import tz_datetime

if TYPE_CHECKING:
    from app.channel_orders.models import ChannelOrder, ChannelOrderFavorite
    from app.channels.models import Channel, ChannelFavorite
    from app.plugins.models import Plugin
    from app.watches.models import Watch


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    username: str | None = Field(default=None, max_length=255)
    server_side_threshold: int = Field(
        default=10_000,
        ge=0,
        le=SERVER_SIDE_THRESHOLD_MAXIMUM,
    )


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=tz_datetime.now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    plugins: list[Plugin] = Relationship(back_populates="user")
    channels: list[Channel] = Relationship(back_populates="user", cascade_delete=True)
    channel_orders: list[ChannelOrder] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    watched_episodes: list[Watch] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    favorite_channels: list[ChannelFavorite] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    favorite_channel_orders: list[ChannelOrderFavorite] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    source_preferences: list[UserSourcePreference] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )

    def add_child(self, child: Plugin | Channel | ChannelOrder) -> None:
        from app.channel_orders.models import ChannelOrder  # noqa: PLC0415
        from app.channels.models import Channel  # noqa: PLC0415

        if isinstance(child, Channel):
            self.channels.append(child)
        elif isinstance(child, ChannelOrder):
            self.channel_orders.append(child)
        else:
            self.plugins.append(child)


class BaseUserSourcePreference(SQLModel):
    """Base model for a `User`'s `Source` preferences."""

    source_key: str = Field()
    enabled: bool = Field(default=True)


class UserSourcePreference(
    BaseUserSourcePreference,
    TimestampIdAndHashMixin,
    table=True,
):
    """Model for a `User`'s `Source` preferences."""

    __table_args__ = PrimaryKeyConstraint("user_id", "source_key")

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    priority: int = Field()
    user: User = Relationship(back_populates="source_preferences")
