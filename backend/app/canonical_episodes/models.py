# TODO: Validate
"""Canonical episode models.

A `CanonicalEpisode` is the episode itself, as opposed to an `Episode`, which is
one website's copy of it. It is what a `Channel` holds, what a `Watch` records,
and what filtering and sorting read, so an episode TMDB lists and a video it has
never heard of are handled by the same query with no special case between them.
"""

import uuid
from datetime import datetime
from typing import ClassVar

from sqlalchemy import CheckConstraint
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
    UniqueConstraint,
)

from app.canonical_seasons.models import CanonicalSeason
from app.models import DateTimeField, TimestampIdAndHashMixin, sortable_field_indexes


# TODO: Validate
class BaseCanonicalEpisode(SQLModel):
    """Base model for a `CanonicalEpisode`."""

    # What makes two copies of this episode one episode rather than two.
    # Namespaced by whoever issued it — "TMDB tv 1234" for a record TMDB holds,
    # "YouTube dQw4w9WgXcQ" for one only YouTube knows about — so no two
    # sources can collide on it. `None` while nothing has claimed the episode.
    key: str | None = Field(default=None)

    # TMDB's own account of the episode, kept as columns rather than read back
    # out of `key`, so nothing has to parse a string to build a link or match
    # against it. Written beside the key, never apart from it.
    tmdb_media_type: str | None = Field(default=None)
    tmdb_id: int | None = Field(default=None)

    name: str | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    release_date: datetime | None = DateTimeField(default=None)
    air_date: datetime | None = DateTimeField(default=None)
    sort_order: int | None = Field(default=None)


# TODO: Validate
class CanonicalEpisode(TimestampIdAndHashMixin, BaseCanonicalEpisode, table=True):
    """Model representing an episode, separate from where it can be watched."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "air_date",
        "duration",
        "episode_number",
        "name",
        "release_date",
        "sort_order",
    ]

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint("key", name="CanonicalEpisode-key-key"),
        UniqueConstraint(
            "tmdb_media_type",
            "tmdb_id",
            name="CanonicalEpisode-tmdb_media_type-tmdb_id-key",
        ),
        CheckConstraint(
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
            name="CanonicalEpisode-tmdb-identity-complete",
        ),
        *sortable_field_indexes("CanonicalEpisode", DIRECT_SORTABLE_FIELDS),
        Index("CanonicalEpisode-canonical_season_id-index", "canonical_season_id"),
    )

    canonical_season_id: uuid.UUID = Field(
        foreign_key="canonicalseason.id",
        ondelete="CASCADE",
    )
    canonical_season: CanonicalSeason = Relationship(
        back_populates="canonical_episodes",
    )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `CanonicalEpisode`."""
        base = "CanonicalEpisode:"
        if self.episode_number is not None:
            base += f" {self.episode_number}"
        if self.name:
            base += f" {self.name}"
        return f"{base} ({self.id})"
