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

from app.models import BaseMediaMixin, DateTimeField, MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source

if TYPE_CHECKING:
    from app.channels.models import ChannelEpisodeFilter
    from app.watches.models import Watch


class BaseEpisode(BaseMediaMixin):
    """Base model representing an Episode."""

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
    """Model representing an Episode."""

    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        UniqueConstraint("id"),
        # Included in SORTABLE_FIELDS.
        Index("Episode-air_date-index", "air_date"),
        Index("Episode-duration-index", "duration"),
        Index("Episode-episode_number-index", "episode_number"),
        Index("Episode-name-index", "name"),
        Index("Episode-release_date-index", "release_date"),
        Index("Episode-sort_order-index", "sort_order"),
        # Used to filter out deleted episodes.
        Index("Episode-deleted_at-index", "deleted_at"),
    )

    SORTABLE_FIELDS: ClassVar[list[str]] = [
        # Direct fields.
        "air_date",
        "duration",
        "episode_number",
        "id",
        "name",
        "release_date",
        "sort_order",
        # Indirect fields.
        "last_watched",
        "random",
        "recently_aired",
        "sequential",
    ]

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
        """Return a string representation of the Episode."""
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
