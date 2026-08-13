# TODO: Validate
"""File models."""

import uuid
from datetime import datetime
from typing import ClassVar, Never, Self, override

from sqlalchemy.orm import contains_eager
from sqlmodel import Field, PrimaryKeyConstraint, Relationship, Session, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models import BaseMediaMixin, DateTimeField, MediaMixin
from app.plugins.models import Plugin
from app.users.models import User


# TODO: Validate
class BaseFile(BaseMediaMixin):
    """Base model for a `File`."""

    # data_timestamp is a required field for files.
    data_timestamp: datetime = DateTimeField()  # pyright: ignore[reportIncompatibleVariableOverride]
    content: str | None = Field(default=None)


# TODO: Validate
class File(BaseFile, MediaMixin[Plugin, Never], table=True):  # pyright: ignore[reportIncompatibleVariableOverride]
    """Model representing a `File`."""

    PARENT_ID_FIELD: ClassVar[str] = "plugin_id"

    __table_args__ = (PrimaryKeyConstraint("plugin_id", "key"),)

    plugin_id: uuid.UUID = Field(foreign_key="plugin.id", ondelete="CASCADE")
    plugin: Plugin = Relationship(back_populates="files")

    # TODO: Validate
    @property
    @override
    def parent(self) -> Plugin:
        return self.plugin

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Never]:
        return []

    # TODO: Validate
    @override
    def _root_record(self, session: Session) -> Plugin:
        return self.plugin

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        return select(cls).join(Plugin)

    # TODO: Validate
    @classmethod
    @override
    def select_with_user_eager(cls) -> SelectOfScalar[Self]:
        return (
            cls.select_with_plugin()
            .join(User)
            .options(
                contains_eager(cls.plugin).contains_eager(Plugin.user),  # type: ignore[arg-type]  # type: ignore[arg-type]
            )
        )

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `File`."""
        base_file = "File:"
        if self.key:
            base_file += f" {self.key}"
        if self.id:
            base_file += f" ({self.id})"
        return f"{self.plugin}\n{base_file}"
