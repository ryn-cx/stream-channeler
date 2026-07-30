# TODO: Validate
import uuid
from datetime import datetime

from pydantic import computed_field
from sqlmodel import (
    DateTime,
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
    UniqueConstraint,
)

from app.episodes.models import Episode
from app.models import TimestampIdAndHashMixin
from app.users.models import User
from app.utils import tz_datetime


class BaseWatch(SQLModel):
    # call-overload - See TimestampAndIdMixin for an explanation.
    watch_date: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        default_factory=tz_datetime.now,
    )

    verified: bool = Field(default=False)


class Watch(TimestampIdAndHashMixin, BaseWatch, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "episode_id", "watch_date"),
        UniqueConstraint("id"),
        # Used in episode_selector and watch services to look up a user's watches.
        Index("Watch-user_id-episode_id-index", "user_id", "episode_id"),
        # Used by cascade deletion when an episode is deleted.
        Index("Watch-episode_id-index", "episode_id"),
        # Used in episode_selector._apply_hide_watched and
        # episode_selector._filter_show_counts to filter by verified watch status.
        Index("Watch-user_id-verified-index", "user_id", "verified"),
        # Used in episode_selector._build_last_watched to aggregate the latest watch
        # date per episode and in episode_selector._apply_recently_aired_sort.
        Index("Watch-watch_date-index", "watch_date"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="watched_episodes")

    # A watch points at the episode that was watched, so renaming that episode's
    # `episode_identifier` never detaches the watch. Reads still group watches by
    # identifier so a watch counts for the same episode from every source.
    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    episode: Episode = Relationship(back_populates="watches")

    @computed_field
    @property
    def episode_identifier(self) -> str:
        """Return the `episode_identifier` of the episode this watch points at."""
        return self.episode.episode_identifier

    def owner_id(self, _session: Session) -> uuid.UUID:
        return self.user_id

    def is_publically_readable(self, _session: Session) -> bool:
        return False
