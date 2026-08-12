# TODO: Validate
"""Canonical season models.

A `CanonicalSeason` is the season itself, as opposed to a `Season`, which is one
website's copy of it. TMDB gives its seasons their own ids, and a film is filed
as a season carrying the film's own number, so the key says the level as well as
the id to keep the two apart.
"""

import uuid
from typing import TYPE_CHECKING, ClassVar

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

    # What makes two copies of this season one season rather than two, and the
    # whole of what says which TMDB record a season is. Namespaced by whoever
    # issued it — "TMDB tv season 3624" for a record TMDB holds, "YouTube
    # dQw4w9WgXcQ" for one only YouTube knows about — so no two sources can
    # collide on it. Unique within one title rather than across all of them,
    # since a plugin only promises a key means one thing under the title holding
    # it. `None` while nothing has claimed the season.
    key: str | None = Field(default=None)

    name: str | None = Field(default=None)
    # The season's own page, as against a copy's `url`, which is where that
    # one website streams it. TMDB's row points at themoviedb.org; a row only
    # one website knows about points wherever that website put it.
    url: str | None = Field(default=None)
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
        UniqueConstraint(
            "canonical_show_id",
            "key",
            name="CanonicalSeason-canonical_show_id-key-key",
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
