# TODO: Validate
"""Canonical season models.

A `CanonicalSeason` is the season itself, as opposed to a `Season`, which is one
website's copy of it. TMDB gives its seasons their own ids, so `tmdb_id` stands
alone here rather than needing the media type its title carries.
"""

import uuid
from typing import TYPE_CHECKING, ClassVar

from sqlalchemy import CheckConstraint
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
    UniqueConstraint,
)

from app.canonical_shows.models import CanonicalShow
from app.models import TimestampIdAndHashMixin, sortable_field_indexes

if TYPE_CHECKING:
    from app.canonical_episodes.models import CanonicalEpisode


# TODO: Validate
class BaseCanonicalSeason(SQLModel):
    """Base model for a `CanonicalSeason`."""

    # What makes two copies of this season one season rather than two.
    # Namespaced by whoever issued it — "TMDB tv 1234" for a record TMDB holds,
    # "YouTube dQw4w9WgXcQ" for one only YouTube knows about — so no two
    # sources can collide on it. `None` while nothing has claimed the season.
    key: str | None = Field(default=None)

    # TMDB's own account of the season, kept as columns rather than read back
    # out of `key`, so nothing has to parse a string to build a link or match
    # against it. Written beside the key, never apart from it.
    tmdb_media_type: str | None = Field(default=None)
    tmdb_id: int | None = Field(default=None)

    name: str | None = Field(default=None)
    season_number: int | None = Field(default=None)
    image_url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)


# TODO: Validate
class CanonicalSeason(TimestampIdAndHashMixin, BaseCanonicalSeason, table=True):
    """Model representing a season, separate from where it can be watched."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "name",
        "season_number",
        "sort_order",
    ]

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint("key", name="CanonicalSeason-key-key"),
        UniqueConstraint(
            "tmdb_media_type",
            "tmdb_id",
            name="CanonicalSeason-tmdb_media_type-tmdb_id-key",
        ),
        CheckConstraint(
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
            name="CanonicalSeason-tmdb-identity-complete",
        ),
        *sortable_field_indexes("CanonicalSeason", DIRECT_SORTABLE_FIELDS),
        Index("CanonicalSeason-canonical_show_id-index", "canonical_show_id"),
    )

    canonical_show_id: uuid.UUID = Field(
        foreign_key="canonicalshow.id",
        ondelete="CASCADE",
    )
    canonical_show: CanonicalShow = Relationship(back_populates="canonical_seasons")

    canonical_episodes: list[CanonicalEpisode] = Relationship(
        back_populates="canonical_season",
        cascade_delete=True,
    )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `CanonicalSeason`."""
        base = "CanonicalSeason:"
        if self.season_number is not None:
            base += f" {self.season_number}"
        if self.name:
            base += f" {self.name}"
        return f"{base} ({self.id})"
