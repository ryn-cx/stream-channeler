# TODO: Validate
"""File models."""

import uuid
from datetime import datetime
from typing import ClassVar, Never, Self, override

from sqlalchemy.orm import contains_eager
from sqlmodel import Field, PrimaryKeyConstraint, Relationship, select
from sqlmodel.sql.expression import SelectOfScalar

from app.models import BaseMediaMixin, ChildMediaMixin, DateTimeField
from app.plugins.models import Plugin


# TODO: Validate
class BaseFile(BaseMediaMixin):
    """Base model for a `File`."""

    # data_timestamp is a required field for files.
    data_timestamp: datetime = DateTimeField()  # pyright: ignore[reportIncompatibleVariableOverride]
    content: str | None = Field(default=None)


# TODO: Validate
class File(BaseFile, ChildMediaMixin[Plugin, Never], table=True):  # pyright: ignore[reportIncompatibleVariableOverride]
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
    def __str__(self) -> str:
        """Return a string representation of the `File`."""
        base_file = "File:"
        if self.key:
            base_file += f" {self.key}"
        if self.id:
            base_file += f" ({self.id})"
        return f"{self.plugin}\n{base_file}"
