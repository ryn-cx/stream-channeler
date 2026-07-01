"""Plugin models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    UniqueConstraint,
)

from app.models import (
    BaseMediaMixin,
    MediaMixin,
    Visibility,
    sortable_field_indexes,
)
from app.users.models import User

if TYPE_CHECKING:
    from app.files.models import File
    from app.sources.models import Source


class BasePlugin(BaseMediaMixin):
    """Base model for a `Plugin`."""

    name: str | None = Field(default=None)
    version: str | None = Field(default=None)
    visibility: Visibility = Field()


class Plugin(BasePlugin, MediaMixin[User, "Source | File"], table=True):
    """Model representing a `Plugin`."""

    DIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = ["id", "name", "visibility"]
    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = []
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("user_id", "key"),
        UniqueConstraint("id"),
        *sortable_field_indexes("Plugin", DIRECT_SORTABLE_FIELDS),
        Index("Plugin-deleted_at-index", "deleted_at"),
    )

    user_id: uuid.UUID = Field(
        foreign_key="user.id",
        ondelete="CASCADE",
    )
    user: User = Relationship(back_populates="plugins")

    sources: list[Source] = Relationship(back_populates="plugin", cascade_delete=True)
    files: list[File] = Relationship(back_populates="plugin", cascade_delete=True)

    @property
    @override
    def parent(self) -> User:
        return self.user

    @override
    def add_child(self, child: Source | File) -> None:
        from app.files.models import File  # noqa: PLC0415

        if isinstance(child, File):
            self.files.append(child)
        else:
            self.sources.append(child)

    @override
    def _root_record(self, session: Session) -> Plugin:
        return self

    @property
    @override
    def children(self) -> list[Source | File]:
        return [*self.sources, *self.files]

    def __str__(self) -> str:
        """Return a string representation of the `Plugin`."""
        base_plugin = "Plugin:"
        if self.key:
            base_plugin += f" {self.key}"
        if self.id:
            base_plugin += f" ({self.id})"
        return base_plugin
