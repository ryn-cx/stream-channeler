# TODO: Validate
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

if TYPE_CHECKING:
    from app.shows.models import Show


class BaseSource(BaseMediaMixin):
    name: str | None = Field(default=None)
    favicon_url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


class Source(BaseSource, MediaMixin[Plugin, "Show"], table=True):
    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = ["id", "name"]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = []
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes("Source", DIRECT_SORTABLE_FIELDS),
        Index("Source-deleted_at-index", "deleted_at"),
    )

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(back_populates="sources")
    shows: list[Show] = Relationship(back_populates="source", cascade_delete=True)

    @override
    def _root_record(self, session: Session) -> Plugin:
        return self.plugin

    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Plugin)

    @property
    @override
    def parent(self) -> Plugin:
        return self.plugin

    @property
    @override
    def children(self) -> list[Show]:
        return self.shows

    def __str__(self) -> str:
        """Return a string representation of the Source."""
        base_source = "Source:"
        if self.name:
            base_source += f" {self.name}"
        if self.key:
            base_source += f" ({self.key})"
        if self.id:
            base_source += f" ({self.id})"
        return f"{self.plugin}\n{base_source}"
