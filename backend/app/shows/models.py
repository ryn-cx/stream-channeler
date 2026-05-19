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

from app.models import BaseMediaMixin, MediaMixin, sortable_field_indexes
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
    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = ["id", "media_type", "name"]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = [
        "episode_count",
        "random",
        "started",
    ]
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("source_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes("Show", DIRECT_SORTABLE_FIELDS),
        Index("Show-deleted_at-index", "deleted_at"),
    )

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
    def _root_record(self, session: Session) -> Plugin:
        return session.exec(
            select(Plugin)
            .select_from(Source)
            .join(Plugin)
            .where(Source.id == self.source_id),
        ).one()

    @property
    @override
    def children(self) -> list[Season]:
        return self.seasons

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
