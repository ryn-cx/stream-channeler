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


class BaseSource(BaseMediaMixin):
    name: str | None = Field(default=None)
    favicon_url: str | None = Field(default=None)
    image_url: str | None = Field(default=None)


if TYPE_CHECKING:
    from app.shows.models import Show


class Source(BaseSource, MediaMixin[Plugin, "Show"], table=True):
    __table_args__ = (
        PrimaryKeyConstraint("plugin_id", "key"),
        UniqueConstraint("id"),
        # Included in SORTABLE_FIELDS.
        Index("Source-name-index", "name"),
        Index("Source-deleted_at-index", "deleted_at"),
    )

    SORTABLE_FIELDS: ClassVar[list[str]] = ["id", "name"]

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(back_populates="sources")
    shows: list[Show] = Relationship(back_populates="source", cascade_delete=True)

    @override
    def get_user_id(self, session: Session) -> uuid.UUID | None:
        return session.exec(
            select(Plugin.user_id).where(Plugin.id == self.plugin_id),
        ).first()

    @override
    def is_public(self, session: Session) -> bool:
        return bool(
            session.exec(
                select(Plugin.public).where(Plugin.id == self.plugin_id),
            ).first(),
        )

    @property
    @override
    def parent(self) -> Plugin:
        return self.plugin

    @property
    @override
    def children(self) -> list[Show]:
        return self.shows

    @property
    def active_shows(self) -> list[Show]:
        return [show for show in self.shows if not show.deleted_at]

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
