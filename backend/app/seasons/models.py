# TODO: Validate
import uuid
from typing import TYPE_CHECKING, ClassVar, override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
)

from app.models import BaseMediaMixin, MediaMixin
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source


class BaseSeason(BaseMediaMixin):
    sort_order: int | None = Field(default=None)
    name: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    season_number: int | None = Field(default=None)


if TYPE_CHECKING:
    from app.channels.models import ChannelSeasonFilter
    from app.episodes.models import Episode


class Season(BaseSeason, MediaMixin[Show, "Episode"], table=True):
    __table_args__ = (
        PrimaryKeyConstraint("show_id", "key"),
        UniqueConstraint("id"),
        # Included in SORTABLE_FIELDS.
        Index("Season-sort_order-index", "sort_order"),
        Index("Season-season_number-index", "season_number"),
        Index("Season-name-index", "name"),
        Index("Season-deleted_at-index", "deleted_at"),
    )

    SORTABLE_FIELDS: ClassVar[list[str]] = [
        # Direct fields.
        "id",
        "name",
        "season_number",
        "sort_order",
        # Indirect fields.
        "random",
        "sequential",
    ]

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

    @property
    def active_episodes(self) -> list[Episode]:
        return [episode for episode in self.episodes if not episode.deleted_at]

    @override
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Show)
            .join(Source)
            .join(Plugin)
            .where(Show.id == self.show_id),
        ).one()

    def __str__(self) -> str:
        """Return a string representation of the Season."""
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
