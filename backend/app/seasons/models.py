"""Season models."""
import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

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

from app.models import BaseMediaMixin, MediaMixin, sortable_field_indexes
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source

if TYPE_CHECKING:
    from app.channels.models import ChannelSeasonFilter
    from app.episodes.models import Episode


class BaseSeason(BaseMediaMixin):
    """Base model for an `Season`."""

    sort_order: int | None = Field(default=None)
    name: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)


class Season(BaseSeason, MediaMixin[Show, "Episode"], table=True):
    """Model representing a `Season`."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "id",
        "name",
        "season_number",
        "sort_order",
    ]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = ["random", "sequential"]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes("Season", DIRECT_SORTABLE_FIELDS),
        Index("Season-deleted_at-index", "deleted_at"),
    )

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(back_populates="seasons")

    episodes: list[Episode] = Relationship(back_populates="season", cascade_delete=True)
    channel_filters: list[ChannelSeasonFilter] = Relationship(
        back_populates="season",
        cascade_delete=True,
    )

    @property
    @override
    def parent(self) -> Show:
        return self.show

    @property
    @override
    def children(self) -> list[Episode]:
        return self.episodes

    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Show)
            .join(Source)
            .join(Plugin)
            .where(Show.id == self.show_id),
        ).one()

    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Show).join(Source).join(Plugin)

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
