# TODO: Validate
import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

from app.constants import SERVER_SIDE_THRESHOLD_MAXIMUM
from app.utils import tz_datetime

if TYPE_CHECKING:
    from app.channels.models import Channel
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
    watched_episodes: list[Watch] = Relationship(
        back_populates="user",
        cascade_delete=True,
    )

    # TODO: This isn't actually used but the implementation is wrong.
    def add_child(self, child: "Plugin | Channel | Watch") -> None:  # noqa: UP037
        from app.plugins.models import Plugin  # noqa: PLC0415

        if isinstance(child, Plugin):
            self.plugins.append(child)
        else:
            self.channels.append(child)

    # TODO: Where is this used?
    @property
    def children(self) -> "list[Plugin]":  # noqa: UP037
        return self.plugins
