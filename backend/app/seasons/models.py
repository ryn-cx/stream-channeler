# TODO: Validate
"""Season models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

from sqlalchemy.orm import contains_eager
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    UniqueConstraint,
    col,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.models import (
    BaseMediaMixin,
    ChildMediaMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.issue_reports.models import SeasonIssueReport

CANONICAL_SORTABLE_FIELDS = [
    "name",
    "season_number",
    "sort_order",
]


# TODO: Validate
class BaseSeason(BaseMediaMixin):
    """The columns a season carries, and so a non-canonical row of one carries too."""

    name: str | None = Field(default=None)
    # The season's own page, as against a non-canonical row's `url`, which is where that
    # one website streams it. TMDB's row points at themoviedb.org; a row only one
    # website knows about points wherever that website put it.
    url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)
    image_url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)


# TODO: Validate
class Season(BaseSeason, ChildMediaMixin[Show, "Episode"], table=True):
    """Model representing a season, and a website's non-canonical row of one.

    The season itself hangs off the title the way a non-canonical row hangs off the
    listing, by the same `show_id`, so one primary key covers both: a `show_id` names
    either a title or a listing and never both at once.
    """

    PARENT_ID_FIELD: ClassVar[str] = "show_id"

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "random",
        "season_number_zero_last",
        "sequential",
        "sequential_zero_last",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        CANONICAL_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        Index("Season-deleted_at-index", "deleted_at"),
        *sortable_field_indexes("Season", CANONICAL_SORTABLE_FIELDS),
    )

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(back_populates="seasons")

    episodes: list[Episode] = Relationship(back_populates="season", cascade_delete=True)

    issue_reports: list[SeasonIssueReport] = Relationship(
        back_populates="season",
        cascade_delete=True,
    )

    # TODO: Validate
    @property
    @override
    def parent(self) -> Show:
        return self.show

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Episode]:
        return self.episodes

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return (
            select(cls)
            .join(Show, col(cls.show_id) == col(Show.id))
            .join(Source)
            .join(Plugin)
        )

    # TODO: Validate
    @classmethod
    def select_with_plugin_eager(cls) -> SelectOfScalar[Self]:
        return cls.select_with_plugin().options(
            contains_eager(cls.show)  # type: ignore[arg-type]
            .contains_eager(Show.source)  # type: ignore[arg-type]
            .contains_eager(Source.plugin),  # type: ignore[arg-type]
        )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Season`."""
        return stringify_season(self, self.show)


# TODO: Validate
def stringify_season(
    season: Season,
    parent: Show,
) -> str:
    """Return a string representation."""
    base_season = f"{type(season).__name__}:"
    if season.season_number is not None:
        base_season += f" {season.season_number} - "
    if season.name:
        base_season += f" {season.name}"
    if season.key:
        base_season += f" ({season.key})"
    if season.id:
        base_season += f" ({season.id})"
    return f"{parent}\n{base_season}"
