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
    from app.channels.models import ChannelSeasonWhiteList
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
        "sort_order",
        "name",
        "season_number",
        "random",
    ]

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship(back_populates="seasons")

    episodes: list[Episode] = Relationship(back_populates="season", cascade_delete=True)
    channel_white_list: list[ChannelSeasonWhiteList] = Relationship(
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
    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id)
            .select_from(Show)
            .join(Source)
            .join(Plugin)
            .where(Show.id == self.show_id),
        ).first()

    @override
    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public)
                .select_from(Show)
                .join(Source)
                .join(Plugin)
                .where(Show.id == self.show_id),
            ).first(),
        )

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
