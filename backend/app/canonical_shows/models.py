# TODO: Validate
"""Canonical show models.

A `CanonicalShow` is the title itself, as opposed to a `Show`, which is one
website's copy of it. Every `Show` points at one, so a title held by three
websites is three `Show`s and a single `CanonicalShow`.

A TMDB identity is optional. When `key` names a TMDB record the title is one
TMDB lists and TMDB owns the metadata here; when it names anything else the
title is one TMDB has no entry for, such as a YouTube channel's uploads, and the
metadata is copied from the only copy there is. Both kinds are filtered and
sorted the same way, because both are rows in this table.
"""

from typing import TYPE_CHECKING, ClassVar

from sqlmodel import (
    Field,
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

    # What makes two copies of this title one title rather than two, and the
    # whole of what says which TMDB record a title is. Namespaced by whoever
    # issued it — "TMDB tv 1399" for a record TMDB holds, "YouTube
    # dQw4w9WgXcQ" for one only YouTube knows about — so no two sources can
    # collide on it. Every row has one from the moment it is made: a title
    # nothing can name is a title nothing can converge on.
    key: str = Field()

    name: str | None = Field(default=None)
    # The title's own page, as against a copy's `url`, which is where that
    # one website streams it. TMDB's row points at themoviedb.org; a row only
    # one website knows about points wherever that website put it.
    url: str | None = Field(default=None)
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
        # Postgres counts NULLs as distinct, so this binds every claimed title
        # to one row while leaving titles nothing has claimed free to be as many
        # rows as there are of them.
        UniqueConstraint("key", name="CanonicalShow-key-key"),
        *sortable_field_indexes("CanonicalShow", DIRECT_SORTABLE_FIELDS),
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
        if self.key:
            base += f" ({self.key})"
        return f"{base} ({self.id})"
