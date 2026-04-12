import uuid
from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Never, override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
    select,
)

from app.models import BaseMediaMixin, DateTimeField, MediaMixin
from app.plugins.models import Plugin
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source


class BaseEpisode(BaseMediaMixin):
    url: str | None = Field(default=None)
    sort_order: int | None = Field(default=None)
    description: str | None = Field(default=None)
    image_url: str | None = Field(default=None)
    episode_number: int | None = Field(default=None)
    name: str | None = Field(default=None)
    duration: int | None = Field(ge=0, default=None)
    release_date: datetime | None = DateTimeField(default=None)
    air_date: datetime | None = DateTimeField(default=None)


if TYPE_CHECKING:
    from app.channels.models import ChannelEpisodeWhiteList
    from app.watches.models import Watch


class Episode(BaseEpisode, MediaMixin[Season, Never], table=True):
    __table_args__ = (
        PrimaryKeyConstraint("season_id", "key"),
        UniqueConstraint("id"),
        # Included in SORTABLE_FIELDS.
        Index("Episode-sort_order-index", "sort_order"),
        Index("Episode-episode_number-index", "episode_number"),
        Index("Episode-name-index", "name"),
        Index("Episode-release_date-index", "release_date"),
        Index("Episode-air_date-index", "air_date"),
        Index("Episode-duration-index", "duration"),
        Index("Episode-deleted_at-index", "deleted_at"),
    )

    SORTABLE_FIELDS: ClassVar[list[str]] = [
        "sort_order",
        "episode_number",
        "name",
        "duration",
        "release_date",
        "air_date",
        "recently_aired",
        "last_watched",
        "random",
    ]

    season_id: uuid.UUID = Field(foreign_key="season.id", ondelete="CASCADE")
    season: Season = Relationship(back_populates="episodes")

    white_lists: list[ChannelEpisodeWhiteList] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )
    watches: list[Watch] = Relationship(
        back_populates="episode",
        cascade_delete=True,
    )

    @override
    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id)
            .select_from(Season)
            .join(Show)
            .join(Source)
            .join(Plugin)
            .where(Season.id == self.season_id),
        ).first()

    @override
    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public)
                .select_from(Season)
                .join(Show)
                .join(Source)
                .join(Plugin)
                .where(Season.id == self.season_id),
            ).first(),
        )

    @property
    @override
    def parent(self) -> Season:
        return self.season

    @property
    @override
    def children(self) -> list[Never]:
        return []

    def __str__(self) -> str:
        """Return a string representation of the Episode."""
        base_episode = "Episode:"
        if self.episode_number:
            base_episode += f" {self.episode_number} - "
        if self.name:
            base_episode += f" {self.name}"
        if self.key:
            base_episode += f" ({self.key})"
        if self.id:
            base_episode += f" ({self.id})"
        return f"{self.season}\n{base_episode}"
