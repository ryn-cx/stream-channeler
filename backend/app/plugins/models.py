# TODO: Validate
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
)

from app.models import BaseMediaMixin, DateTimeField, MediaMixin, Visibility
from app.users.models import User

if TYPE_CHECKING:
    from app.sources.models import Source


class BasePlugin(BaseMediaMixin):
    name: str | None = Field(default=None)
    version: str | None = Field(default=None)
    visibility: Visibility = Field()


class Plugin(BasePlugin, MediaMixin[User, "Source | File"], table=True):
    __table_args__ = (
        PrimaryKeyConstraint("user_id", "key"),
        UniqueConstraint("id"),
        Index("Plugin-deleted_at-index", "deleted_at"),
    )

    # Direct fields.
    SORTABLE_FIELDS: ClassVar[list[str]] = ["id", "name", "visibility"]

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

    @property
    def active_sources(self) -> list[Source]:
        return [source for source in self.sources if not source.deleted_at]

    def __str__(self) -> str:
        """Return a string representation of the Plugin."""
        base_plugin = "Plugin:"
        if self.key:
            base_plugin += f" {self.key}"
        if self.id:
            base_plugin += f" ({self.id})"
        return base_plugin


class BaseFile(BaseMediaMixin):
    # data_timestamp is a required field for files.
    data_timestamp: datetime = DateTimeField()  # pyright: ignore[reportIncompatibleVariableOverride]
    content: str | None = Field(default=None)


# data_timestamp is a required value for files.
class File(BaseFile, MediaMixin[Plugin, Never], table=True):  # pyright: ignore[reportIncompatibleVariableOverride]
    __table_args__ = (PrimaryKeyConstraint("plugin_id", "key"),)

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(back_populates="files")

    @property
    @override
    def parent(self) -> Plugin:
        return self.plugin

    @property
    @override
    def children(self) -> list[Never]:
        return []

    @override
    def _root_record(self, _session: Session) -> Plugin:
        return self.plugin

    def __str__(self) -> str:
        """Return a string representation of the File."""
        base_file = "File:"
        if self.key:
            base_file += f" {self.key}"
        if self.id:
            base_file += f" ({self.id})"
        return f"{self.plugin}\n{base_file}"
