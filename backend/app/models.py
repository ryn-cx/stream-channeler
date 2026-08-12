# TODO: Validate
"""Shared models."""

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from datetime import datetime
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, Self

from sqlalchemy import util
from sqlmodel import DateTime, Field, Index, Session, SQLModel
from sqlmodel.sql.expression import SelectOfScalar

from app.utils import tz_datetime

if TYPE_CHECKING:
    from sqlalchemy import Table
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.channel_orders.models import ChannelOrder
    from app.channels.models import Channel
    from app.episodes.models import Episode
    from app.files.models import File
    from app.plugins.models import Plugin
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source
    from app.users.models import User


# This is a partial function because it reduces the number of locations that need to
# have a "# type: ignore[call-overload]" comment. Ignoring this error is acceptable
# because the official example for implementing a DateTime field also ignore the error:
# https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/models.py
DateTimeField = partial(Field, sa_type=DateTime(timezone=True))  # type: ignore[call-overload]


# TODO: Validate
class SupportsDataTimestamp(Protocol):
    # TODO: Validate
    @property
    def data_timestamp(self) -> datetime: ...


# A sortable field ending in this is the same sort with the number 0 pushed past
# every other number instead of ahead of them, which is where a season or episode
# numbered 0 belongs when it is the specials rather than the first of the run.
ZERO_LAST_SUFFIX = "_zero_last"


# TODO: Validate
def sortable_field_indexes(
    model_name: str,
    direct_sortable_fields: Iterable[str],
    already_indexed: Iterable[str] = (),
) -> tuple[Index, ...]:
    """Build an `Index` for each field that can be used for sorting by the user.

    `id` is already indexed by the primary key, and `already_indexed` names the
    fields the table indexes itself, which an index built here would collide with.
    """
    skipped = {"id", *already_indexed}
    return tuple(
        Index(f"{model_name}-{field}-index", field)
        for field in direct_sortable_fields
        if field not in skipped
    )


# TODO: Validate
class Visibility(StrEnum):
    """Visibility enum for `Channel`s and `Plugin`s."""

    public = "public"
    unlisted = "unlisted"
    private = "private"


# TODO: Validate
class RootRecordMixin(ABC):
    """Mixin for any model that a `User` can own.

    Subclasses must implement `root_record`.
    """

    # TODO: Validate
    @abstractmethod
    def _root_record(self, session: Session) -> Channel | Plugin | ChannelOrder:
        """Return the root record directly owned by the `User`."""

    # TODO: Validate
    def owner_id(self, session: Session) -> uuid.UUID:
        """Return the `id` of the `User` who owns this record."""
        return self._root_record(session).user_id

    # TODO: Validate
    def is_publically_readable(self, session: Session) -> bool:
        """Return true if this record's `visibility` is `public` or `unlisted`."""
        return self._root_record(session).visibility in (
            Visibility.public,
            Visibility.unlisted,
        )

    # TODO: Validate
    def is_readable(self, session: Session, user: User | None) -> bool:
        """Return whether `user` can read this record.

        Returns true if any of the following are true:
        - The record's `visibility` is `public` or `unlisted`.
        - The `user` is the owner of the record or a superuser.
        """
        if self.is_publically_readable(session):
            return True
        return user is not None and (
            user.id == self.owner_id(session) or user.is_superuser
        )


# TODO: Validate
class TimestampIdAndHashMixin(SQLModel):
    """Mixin that adds `id`, `created_at`, and `modified_at` fields to a model.

    Fields: `id`, `created_at`, and `modified_at`.
    """

    # id is a uuid so the name id makes it easier to differentiate between the id field
    # and the key field.
    id: uuid.UUID = Field(unique=True, default_factory=uuid.uuid4)

    created_at: datetime = DateTimeField(default_factory=tz_datetime.now)
    modified_at: datetime = DateTimeField(
        sa_column_kwargs={"onupdate": tz_datetime.now},
        default_factory=tz_datetime.now,
    )

    # TODO: Validate
    def __hash__(self) -> int:
        """Return a hash representation of the record based on the `id`."""
        return hash(self.id)

    # TODO: Validate
    def __eq__(self, other: object) -> bool:
        """Two records are equal when they share the same `id`."""
        return isinstance(other, TimestampIdAndHashMixin) and self.id == other.id


# TODO: Validate
class BaseMediaMixin(SQLModel):
    """Mixin for base media models.

    Fields: `key`, `data_timestamp`, `update_at`, `deleted_at`, and `extra`.
    """

    # key is a surrogate key so the name key makes it easier to differentiate between
    # the key field and the id field.
    key: str = Field(min_length=1)
    data_timestamp: datetime | None = DateTimeField(default=None)
    update_at: datetime | None = DateTimeField(default=None)
    deleted_at: datetime | None = DateTimeField(default=None)

    # Allows plugins to store custom information beyond the database's structure.
    extra: str | None = Field(default=None)


# TODO: Validate
class MediaMixin[
    ParentT: User | Plugin | Source | Show | Season,
    ChildT: Plugin | Source | Show | Season | Episode | File,
](TimestampIdAndHashMixin, BaseMediaMixin, RootRecordMixin, ABC):
    # Will be automatically set when table=True, required for type checking
    # parent_id_field.
    __table__: ClassVar[Table]

    """Mixin for media models.

    Subclasses must implement `parent`, `children`, `root_record`, and
    `select_with_plugin`.
    """

    # TODO: Validate
    @property
    @abstractmethod
    def parent(self) -> ParentT:
        """Return the parent of the record.

        - `Plugin` -> `User`
        - `Source` -> `Plugin`
        - `Show` -> `Source`
        - `Season` -> `Show`
        - `Episode` -> `Season`
        """

    # TODO: Validate
    @property
    @abstractmethod
    def children(self) -> list[ChildT]:
        """Return the direct children of the record.

        - `Plugin` -> `Source | Files`
        - `Source` -> `Show`
        - `Show` -> `Season`
        - `Season` -> `Episode`
        - `Episode` -> `[]`
        """

    # TODO: Validate
    @property
    def active_children(self) -> list[ChildT]:
        """Return the direct children of the record that are not deleted.

        - `Plugin` -> `Source | Files`
        - `Source` -> `Show`
        - `Show` -> `Season`
        - `Season` -> `Episode`
        - `Episode` -> `[]`
        """
        return [child for child in self.children if child.deleted_at is None]

    # TODO: Validate
    @classmethod
    @abstractmethod
    def select_with_plugin(cls) -> SelectOfScalar[Any]:
        """Return a select joined to `Plugin`."""

    # TODO: Validate
    @classmethod
    @abstractmethod
    def select_with_user_eager(cls) -> SelectOfScalar[Any]:
        """Return a select joined to `User` with contains_eager."""

    # TODO: Validate
    @classmethod
    def get(  # noqa: PLR0913 - Copied from wrapped function
        cls,
        session: Session,
        parent: ParentT,
        key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Self | None:
        """Get a record by its `parent` and `key` if it exists.

        This is a wrapper around `db.get` for easier use with composite primary keys.

        Returns:
            The record if found, else `None`.

        """
        return session.get(
            cls,
            (parent.id, key),
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
        parent: ParentT,
        key: str,
        *,
        options: Sequence[ORMOption] | None = None,
        populate_existing: bool = False,
        with_for_update: ForUpdateParameter = None,
        identity_token: Any | None = None,  # noqa: ANN401 - Copied from wrapped function
        execution_options: OrmExecuteOptionsParameter = util.EMPTY_DICT,
        bind_arguments: dict[str, Any] | None = None,
    ) -> Self:
        """Get a record by its `parent` and `key`, raising if not found.

        This is a wrapper around `db.get_one` for easier use with composite primary
        keys.

        Returns:
            The record.

        Raises:
            NoResultFound: If no matching record is found.

        """
        return session.get_one(
            cls,
            (parent.id, key),
            options=options,
            populate_existing=populate_existing,
            with_for_update=with_for_update,
            identity_token=identity_token,
            execution_options=execution_options,
            bind_arguments=bind_arguments,
        )

    # TODO: Validate
    @classmethod
    def get_from_memory(
        cls,
        session: Session,
        parent: ParentT,
        key: str,
    ) -> Self | None:
        """Get a record by its `parent` and `key` from the session.

        This is a direct lookup in `db.identity_map` and does not query the database.

        Returns:
            The record if found in the identity map, else `None`.

        """
        return session.identity_map.get((cls, (parent.id, key), None))

    # TODO: Validate
    @classmethod
    def get_one_from_memory(
        cls,
        session: Session,
        parent: ParentT,
        key: str,
    ) -> Self:
        """Get a record by its `parent` and `key` from the session, raising if not found.

        This is a direct lookup in `db.identity_map` and does not query the database.

        Returns:
            The record.

        Raises:
            KeyError: If no matching record is found in the identity map.

        """
        return session.identity_map[(cls, (parent.id, key), None)]

    # TODO: Validate
    def set_update_at(
        self,
        new_update_at_value: datetime | None,
        files: Sequence[SupportsDataTimestamp] | None = None,
    ) -> None:
        """Set `update_at` based its current value and `new_update_at_value`."""
        files = files or []
        # If the existing update_at is older than data_timestamp the update has
        # been completed and update_at can be cleared.
        if (
            self.update_at
            and self.data_timestamp
            and self.update_at < self.data_timestamp
        ):
            self.update_at = None

        # If every file is newer than the existing update_at the update has been
        # completed and update_at can be cleared.
        if (
            self.update_at
            and files
            and all(file.data_timestamp > self.update_at for file in files)
        ):
            self.update_at = None

        if not new_update_at_value:
            return

        # If the existing data_timestamp is newer than the new update_at value update_at
        # can be ignored because the data is already up to date.
        if self.data_timestamp and self.data_timestamp >= new_update_at_value:
            return

        # If every file is newer than the new update_at value the data is already up to
        # date and the new value can be ignored.
        if files and all(file.data_timestamp > new_update_at_value for file in files):
            return

        # If the new update_at is before the existing update_at the existing update_at
        # should be replaced so the updates occur as soon as possible.
        if self.update_at is None or new_update_at_value < self.update_at:
            self.update_at = new_update_at_value

    # TODO: Validate
    def add_child(self, child: ChildT) -> None:
        """Add a child to the record."""
        self.children.append(child)

    # TODO: Validate
    @classmethod
    def parent_id_field(cls) -> str:
        """Return the name of the parent id column."""
        return next(
            column.name for column in cls.__table__.columns if column.foreign_keys
        )

    # TODO: Consider implementing a recursive version of this so only one upsert needs
    # to be called when upserting a tree of records.
    # TODO: Validate
    def upsert(
        self,
        parent: ParentT,
        existing_record: Self | None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        """Upsert the record.

        Args:
            parent: The parent record to upsert onto.
            existing_record: The existing record to update, or `None` if no existing
                record exists.
            protected_keys: A set of keys to exclude from updates when an existing
                record is provided.

        """
        if protected_keys is None:
            protected_keys = set()
        if existing_record:
            # id:  automatically generated when making a model, but that value should
            # only be used for new entries. When upserting the original id should be
            # preserved.
            # created_at: set by the database.
            # modified_at: set by the database.
            protected_keys = protected_keys | {"id", "created_at", "modified_at"}
            dumped = self.model_dump(exclude=protected_keys)
            existing_record.sqlmodel_update(dumped)
            return existing_record
        # self will always be a child of parent
        parent.add_child(self)  # type: ignore[arg-type]
        return self

    # TODO: Validate
    def upsert_and_set_update_at(
        self,
        parent: ParentT,
        existing_record: Self | None,
        files: Sequence[SupportsDataTimestamp] | None = None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        """Upsert and automatically set the `update_at` timestamp."""
        if protected_keys is None:
            protected_keys = {"update_at"}
        else:
            protected_keys.add("update_at")

        record = self.upsert(parent, existing_record, protected_keys)
        if existing_record:
            record.set_update_at(self.update_at, files)
        return record

    # TODO: Validate
    def soft_delete(
        self,
        timestamp: datetime | None = None,
        *,
        recursive: bool = True,
    ) -> None:
        """Soft delete the record.

        If the record is already deleted, the existing `deleted_at` value will be
        kept.

        Args:
            timestamp: The timestamp to set for `deleted_at`. If `None`, the current
                time will be used.
            recursive: Whether to also soft delete all children of the record.

        """
        if self.deleted_at is None:
            self.deleted_at = timestamp or tz_datetime.now()

        if recursive:
            for child in self.children:
                child.soft_delete(timestamp)

    # TODO: Validate
    def soft_undelete(self, *, recursive: bool = True) -> None:
        """Soft undelete the record.

        If the record is not deleted `soft_undelete` does nothing.

        Args:
            recursive: Whether to also soft undelete all children of the record.

        """
        self.deleted_at = None
        if recursive:
            for child in self.children:
                child.soft_undelete()

    # TODO: Validate
    def soft_delete_missing_children(self, found_keys: Iterable[str]) -> None:
        """Soft delete children whose keys are not in `found_keys`."""
        found_keys = set(found_keys)
        for child in self.children:
            if child.key not in found_keys:
                child.soft_delete()
