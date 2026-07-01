"""Snapshot models."""

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

from app.episodes.models import Episode
from app.models import RootRecordMixin, TimestampIdAndHashMixin, Visibility
from app.users.models import User


class BaseSnapshot(SQLModel):
    """Base model for a `Snapshot`."""

    name: str | None = Field(default=None)
    visibility: Visibility = Field()
    anonymous: bool = Field(default=False)


class Snapshot(BaseSnapshot, TimestampIdAndHashMixin, RootRecordMixin, table=True):
    """Model representing a `Snapshot`."""

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Used to list all snapshots owned by a user.
        Index("Snapshot-user_id-index", "user_id"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship(back_populates="snapshots")
    score: int = Field(default=0)

    episodes: list[SnapshotEpisode] = Relationship(
        back_populates="snapshot",
        cascade_delete=True,
        sa_relationship_kwargs={"order_by": "SnapshotEpisode.position"},
    )

    @override
    def _root_record(self, session: Session) -> Snapshot:
        return self


class BaseSnapshotEpisode(SQLModel):
    """Base model for a `SnapshotEpisode`."""

    # Position of the episode in the snapshot (0-indexed).
    position: int = Field()


class SnapshotEpisode(BaseSnapshotEpisode, TimestampIdAndHashMixin, table=True):
    """Model representing an `Episode` that belongs to a `Snapshot`."""

    __table_args__ = (
        # The same snapshot cannot have two episodes at the same position.
        PrimaryKeyConstraint("snapshot_id", "position"),
        # Used to cascade deletions when an episode is deleted.
        Index("SnapshotEpisode-episode_id-index", "episode_id"),
    )

    snapshot_id: uuid.UUID = Field(foreign_key="snapshot.id", ondelete="CASCADE")
    snapshot: Snapshot = Relationship(back_populates="episodes")

    episode_id: uuid.UUID = Field(foreign_key="episode.id", ondelete="CASCADE")
    episode: Episode = Relationship()
