"""Episode models."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Never, override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
)

from app.models import BaseMediaMixin, DateTimeField, MediaMixin, sortable_field_indexes
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

if TYPE_CHECKING:
    from app.channels.models import ChannelEpisodeFilter
    from app.watches.models import Watch


class BaseEpisode(BaseMediaMixin):
    """Base model for an `Episode`."""

    url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    name: str | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    release_date: datetime | None = DateTimeField(default=None)
    air_date: datetime | None = DateTimeField(default=None)


class Episode(BaseEpisode, MediaMixin[Season, Never], table=True):
    """Model representing an episode."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "air_date",
        "duration",
        "episode_number",
        "id",
        "name",
        "release_date",
        "sort_order",
    ]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "last_watched_completed",
        "last_watched_incomplete",
        "random",
        "recently_aired",
        "saved_order",
        "sequential",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes("Episode", DIRECT_SORTABLE_FIELDS),
        Index("Episode-deleted_at-index", "deleted_at"),
    )

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(back_populates="episodes")

    channel_filters: list[ChannelEpisodeFilter] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )
    watches: list[Watch] = Relationship(back_populates="episode", cascade_delete=True)

    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Season)
            .join(Show)
            .join(Source)
            .join(Plugin)
            .where(Season.id == self.season_id),
        ).one()

    @property
    @override
    def parent(self) -> Season:
        return self.season

    @property
    @override
    def children(self) -> list[Never]:
        return []

    def __str__(self) -> str:
        """Return a string representation of the `Episode`."""
        base_episode = "Episode:"
        if self.episode_number:
            base_episode += f" {self.episode_number} - "
        if self.name:
            base_episode += f" {self.name}"
        if self.key:
            base_episode += f" ({self.key})"
        if self.id:
            base_episode += f" ({self.id})"
        return f"{self.season}\n{base_episode}"
