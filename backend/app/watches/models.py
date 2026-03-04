import uuid
from datetime import datetime

from sqlmodel import (
    DateTime,
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
    UniqueConstraint,
)

from app.episodes.models import Episode
from app.models import TimestampIdMixin
from app.users.models import User
from app.utils import tz_datetime


class BaseEpisodeWatch(SQLModel):
    # call-overload - See TimestampIdMixin for an explanation.
    watch_date: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        default_factory=tz_datetime.now,
    )

    verified: bool = Field(default=False)


class EpisodeWatch(TimestampIdMixin, BaseEpisodeWatch, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "episode_id", "watch_date"),
        UniqueConstraint("id"),
        # Filtering options.
        Index("EpisodeWatch-user_id-episode_id-index", "user_id", "episode_id"),
        Index("EpisodeWatch-user_id-verified-index", "user_id", "verified"),
        Index("EpisodeWatch-watch_date-index", "watch_date"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="watched_episodes")

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    episode: Episode = Relationship(back_populates="watches")
