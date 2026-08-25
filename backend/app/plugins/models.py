# TODO: Validate
"""Plugin models."""

from typing import TYPE_CHECKING, Any, ClassVar, Self, override

from sqlalchemy import util
from sqlalchemy.orm import object_session
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
    SupportsDataTimestamp,
    sortable_field_indexes,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.files.models import File
    from app.sources.models import Source

DIRECT_SORTABLE_FIELDS = ["id", "name"]


# TODO: Validate
class BasePlugin(BaseMediaMixin):
    """Base model for a `Plugin`."""

    name: str | None = Field(default=None)
    version: str | None = Field(default=None)


# TODO: Validate
class Plugin(BasePlugin, MediaMixin["Source | File"], table=True):
    """Model representing a `Plugin`."""

    INDIRECT_SORTABLE_FIELDS: ClassVar[list[str]] = []
    SORTABLE_FIELDS: ClassVar[list[str]] = (
        DIRECT_SORTABLE_FIELDS + INDIRECT_SORTABLE_FIELDS
    )

    __table_args__ = (
        PrimaryKeyConstraint("key"),
        UniqueConstraint("id"),
        *sortable_field_indexes("Plugin", DIRECT_SORTABLE_FIELDS),
        Index("Plugin-deleted_at-index", "deleted_at"),
    )

    sources: list[Source] = Relationship(back_populates="plugin", cascade_delete=True)
    files: list[File] = Relationship(back_populates="plugin", cascade_delete=True)

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
    @classmethod
    @override
    def select_with_plugin(cls) -> SelectOfScalar[Self]:
        # A `Plugin` is its own owning `Plugin`, so there is nothing to join.
        return select(cls)

    # TODO: Validate
    @property
    @override
    def children(self) -> list[Source | File]:
        return [*self.sources, *self.files]

    # TODO: Validate
    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Self | None:
        return session.get(
            cls,
            key,
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    # TODO: Validate
    @classmethod
    def get_one(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Self:
        return session.get_one(
            cls,
            key,
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    # TODO: Validate
    def upsert(
        self,
        session: Session,
        existing_record: Self | None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        if protected_keys is None:
            protected_keys = set()
        if existing_record:
            return self._update_existing(existing_record, protected_keys)
        session.add(self)
        return self

    # TODO: Validate
    def upsert_and_set_update_at(
        self,
        session: Session,
        existing_record: Self | None,
        files: Sequence[SupportsDataTimestamp] | None = None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        """Upsert and automatically set the `update_at` timestamp."""
        if protected_keys is None:
            protected_keys = {"update_at"}
        else:
            protected_keys.add("update_at")

        record = self.upsert(session, existing_record, protected_keys)
        if existing_record:
            record.set_update_at(self.update_at, files)
        return record

    # TODO: Validate
    def __str__(self) -> str:
        """Return a string representation of the `Plugin`."""
        base_plugin = "Plugin:"
        if self.key:
            base_plugin += f" {self.key}"
        if self.id:
            base_plugin += f" ({self.id})"
        return base_plugin
