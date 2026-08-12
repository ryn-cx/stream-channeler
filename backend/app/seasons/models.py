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
    Session,
    UniqueConstraint,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.canonical_media.keys import SEASON_LEVEL, tmdb_id_of
from app.canonical_seasons.models import CanonicalSeason
from app.models import (
    BaseMediaMixin,
    MediaMixin,
    sortable_field_indexes,
)
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.issue_reports.models import SeasonIssueReport


# TODO: Validate
class BaseSeason(BaseMediaMixin):
    """Base model for an `Season`."""

    sort_order: int | None = Field(default=None)
    name: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)


# TODO: Validate
# TODO: Validate
class Season(BaseSeason, MediaMixin[Show, "Episode"], table=True):
    """Model representing a `Season`."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "name",
        "season_number",
        "sort_order",
    ]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "random",
        "season_number_zero_last",
        "sequential",
        "sequential_zero_last",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes(
            "Season",
            DIRECT_SORTABLE_FIELDS,
        ),
        Index("Season-deleted_at-index", "deleted_at"),
        Index("Season-canonical_season_id-index", "canonical_season_id"),
    )

    # The season this is a copy of. Never absent: `canonical_media.hooks`
    # gives a record one at the flush, before it can reach the database.
    canonical_season_id: uuid.UUID = Field(
        foreign_key="canonicalseason.id",
        ondelete="RESTRICT",
    )
    canonical_season: CanonicalSeason = Relationship()

    # TODO: Validate
    @property
    def tmdb_id(self) -> int | None:
        """The TMDB season this is a copy of, if TMDB has a record of it."""
        if self.canonical_season is None:
            return None
        return tmdb_id_of(self.canonical_season.key, SEASON_LEVEL)

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
    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Show)
            .join(Source)
            .join(Plugin)
            .where(Show.id == self.show_id),
        ).one()

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Show).join(Source).join(Plugin)

    # TODO: Validate
    @classmethod
    @override
    def select_with_user_eager(cls) -> SelectOfScalar[Self]:
        return (
            cls.select_with_plugin()
            .join(User)
            .options(
                contains_eager(cls.show)  # type: ignore[arg-type]
                .contains_eager(Show.source)  # type: ignore[arg-type]
                .contains_eager(Source.plugin)  # type: ignore[arg-type]
                .contains_eager(Plugin.user),  # type: ignore[arg-type]
            )
        )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Season`."""
        base_season = "Season:"
        if self.season_number:
            base_season += f" {self.season_number} - "
        if self.name:
            base_season += f" {self.name}"
        if self.key:
            base_season += f" ({self.key})"
        if self.id:
            base_season += f" ({self.id})"
        return f"{self.show}\n{base_season}"
