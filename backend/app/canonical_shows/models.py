# TODO: Validate
"""Canonical show models.

A `CanonicalShow` is the title itself, as opposed to a `Show`, which is one
website's copy of it. Every `Show` points at one, so a title held by three
websites is three `Show`s and a single `CanonicalShow`.

A TMDB identity is optional. When `tmdb_id` is set the title is one TMDB lists
and TMDB owns the metadata here; when it is `None` the title is one TMDB has no
entry for, such as a YouTube channel's uploads, and the metadata is copied from
the only copy there is. Both kinds are filtered and sorted the same way, because
both are rows in this table.
"""

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

from app.models import TimestampIdAndHashMixin, sortable_field_indexes

if TYPE_CHECKING:
    from app.canonical_seasons.models import CanonicalSeason


# TODO: Validate
class BaseCanonicalShow(SQLModel):
    """Base model for a `CanonicalShow`."""

    # What makes two copies of this title one title rather than two.
    # Namespaced by whoever issued it — "TMDB tv 1234" for a record TMDB holds,
    # "YouTube dQw4w9WgXcQ" for one only YouTube knows about — so no two
    # sources can collide on it. `None` while nothing has claimed the title.
    key: str | None = Field(default=None)

    # TMDB's own account of the title, kept as columns rather than read back
    # out of `key`, so nothing has to parse a string to build a link or match
    # against it. Written beside the key, never apart from it.
    tmdb_media_type: str | None = Field(default=None)
    tmdb_id: int | None = Field(default=None)

    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    icon: str | None = Field(default=None, max_length=32)


# TODO: Validate
class CanonicalShow(TimestampIdAndHashMixin, BaseCanonicalShow, table=True):
    """Model representing a title, separate from where it can be watched."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "media_type",
        "name",
    ]

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # TMDB numbers films and series separately, so the media type is part of
        # the identity. Postgres counts NULLs as distinct, so this binds every
        # TMDB title to one row while leaving titles TMDB has never heard of
        # free to be as many rows as there are of them.
        UniqueConstraint("key", name="CanonicalShow-key-key"),
        UniqueConstraint(
            "tmdb_media_type",
            "tmdb_id",
            name="CanonicalShow-tmdb_media_type-tmdb_id-key",
        ),
        CheckConstraint(
            "(tmdb_media_type IS NULL) = (tmdb_id IS NULL)",
            name="CanonicalShow-tmdb-identity-complete",
        ),
        *sortable_field_indexes("CanonicalShow", DIRECT_SORTABLE_FIELDS),
        Index("CanonicalShow-tmdb_id-index", "tmdb_id"),
    )

    canonical_seasons: list[CanonicalSeason] = Relationship(
        back_populates="canonical_show",
        cascade_delete=True,
    )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `CanonicalShow`."""
        base = "CanonicalShow:"
        if self.name:
            base += f" {self.name}"
        if self.tmdb_id:
            base += f" (TMDB {self.tmdb_media_type} {self.tmdb_id})"
        return f"{base} ({self.id})"
