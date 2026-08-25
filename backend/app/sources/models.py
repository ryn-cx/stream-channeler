# TODO: Validate
import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

from sqlalchemy.orm import contains_eager
from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    UniqueConstraint,
    select,
)
from sqlmodel.sql.expression import SelectOfScalar

from app.models import BaseMediaMixin, ChildMediaMixin, sortable_field_indexes
from app.plugins.models import Plugin

if TYPE_CHECKING:
    from app.shows.models import Show

DIRECT_SORTABLE_FIELDS = ["id", "name"]


# TODO: Validate
class BaseSource(BaseMediaMixin):
    name: str | None = Field(default=None)
    favicon_url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


# TODO: Validate
class Source(BaseSource, ChildMediaMixin[Plugin, "Show"], table=True):
    PARENT_ID_FIELD: ClassVar[str] = "plugin_id"

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

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Plugin)

    # TODO: Validate
    @classmethod
    def select_with_plugin_eager(cls) -> SelectOfScalar[Self]:
        return cls.select_with_plugin().options(
            contains_eager(cls.plugin),  # type: ignore[arg-type]
        )

    # TODO: Validate
    @property
    @override
    def parent(self) -> Plugin:
        return self.plugin

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Show]:
        return self.shows

    # TODO: Validate
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
