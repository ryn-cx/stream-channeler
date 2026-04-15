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
from app.sources.models import Source


class BaseShow(BaseMediaMixin):
    name: str | None = Field(default=None)
    media_type: str | None = Field(default=None)
    description: str | None = Field(default=None)
    url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


if TYPE_CHECKING:
    from app.channels.models import ChannelShow
    from app.seasons.models import Season


# The name "Show" was used instead of "Series" because it has a distinct singular and
# plural form and some people may use "Series" to refer to a "Season" so the word "Show"
# is less ambiguous and more flexible.
class Show(BaseShow, MediaMixin[Source, "Season"], table=True):
    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        # Included in SORTABLE_FIELDS.
        Index("Show-name-index", "name"),
        Index("Show-media_type-index", "media_type"),
        Index("Show-deleted_at-index", "deleted_at"),
    )

    SORTABLE_FIELDS: ClassVar[list[str]] = [
        "id",
        "name",
        "media_type",
        "started",
        "episode_count",
        "random",
    ]

    source_id: uuid.UUID = Field(foreign_key="source.id", ondelete="CASCADE")
    source: Source = Relationship(back_populates="shows")

    seasons: list[Season] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    channels: list[ChannelShow] = Relationship(
        back_populates="show",
        cascade_delete=True,
    )

    @override
    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id)
            .select_from(Source)
            .join(Plugin)
            .where(Source.id == self.source_id),
        ).first()

    @override
    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public)
                .select_from(Source)
                .join(Plugin)
                .where(Source.id == self.source_id),
            ).first(),
        )

    @property
    @override
    def children(self) -> list[Season]:
        return self.seasons

    @property
    def active_seasons(self) -> list[Season]:
        return [season for season in self.seasons if not season.deleted_at]

    @property
    @override
    def parent(self) -> Source:
        return self.source

    def __str__(self) -> str:
        """Return a string representation of the Show."""
        base_show = "Show:"
        if self.name:
            base_show += f" {self.name}"
        if self.key:
            base_show += f" ({self.key})"
        if self.id:
            base_show += f" ({self.id})"
        return f"{self.source}\n{base_show}"
