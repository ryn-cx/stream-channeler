import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.utils import tz_datetime

if TYPE_CHECKING:
    from app.channels.models import Channel
    from app.media.models import EpisodeWatch, Plugin


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=tz_datetime.now,
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
    )
    channels: list[Channel] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    watched_episodes: list[EpisodeWatch] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )
    plugins: list[Plugin] = Relationship(
        back_populates="user",
    )
