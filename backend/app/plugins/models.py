# TODO: Validate
"""Plugin models."""

import uuid
from typing import TYPE_CHECKING, ClassVar, Self, override

from sqlalchemy.orm import contains_eager, object_session
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

DIRECT_SORTABLE_FIELDS = ["id", "name", "visibility"]


# TODO: Validate
class BasePlugin(BaseMediaMixin):
    """Base model for a `Plugin`."""

    visibility: Visibility = Field()
    anonymous: bool = Field()
    name: str | None = Field(default=None)
    version: str | None = Field(default=None)


# TODO: Validate
class Plugin(BasePlugin, MediaMixin[User, "Source | File"], table=True):
    """Model representing a `Plugin`."""

    PARENT_ID_FIELD: ClassVar[str] = "user_id"

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

    # TODO: Validate
    @property
    @override
    def parent(self) -> User:
        return self.user

    # TODO: Validate
    @override
    def add_child(self, child: Source | File) -> None:
        from app.files.models import File  # noqa: PLC0415

        if isinstance(child, File):
            # Appending to self.files force-loads the entire files collection, which is
            # O(number of files) per write. The plugin_id is already set, so add the
            # record to the session directly to avoid loading the collection.
            session = object_session(self)
            if not session:
                msg = "Plugin must be attached to a session to add a child"
                raise RuntimeError(msg)

            session.add(child)
        else:
            self.sources.append(child)

    # TODO: Validate
    @override
    def _root_record(self, session: Session) -> Plugin:
        return self

    # TODO: Validate
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        # A `Plugin` is its own owning `Plugin`, so there is nothing to join.
        return select(cls)

    # TODO: Validate
    @classmethod
    @override
    def select_with_user_eager(cls) -> SelectOfScalar[Self]:
        return (
            cls.select_with_plugin()
            .join(User)
            .options(
                contains_eager(cls.user),  # type: ignore[arg-type]
            )
        )

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Source | File]:
        return [*self.sources, *self.files]

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Plugin`."""
        base_plugin = "Plugin:"
        if self.key:
            base_plugin += f" {self.key}"
        if self.id:
            base_plugin += f" ({self.id})"
        return base_plugin
