"""Shared models."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from datetime import datetime
from enum import StrEnum
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, Self

from sqlalchemy import util
from sqlmodel import DateTime, Field, Session, SQLModel

from app.utils import tz_datetime


class Visibility(StrEnum):
    """Visibility level for `Channel`, `Plugin`, and `Playlist` records."""

    public = "public"
    unlisted = "unlisted"
    private = "private"


class _RootRecord(Protocol):
    user_id: uuid.UUID
    visibility: Visibility


class RootRecordMixin(ABC):
    """Shared visibility/ownership methods.

    Used by any record that can resolve itself to a "root" record carrying
    `user_id` and `visibility` columns.

    Subclasses implement `_root_record(session)`:

    - `Channel`, `Playlist`, `Plugin` -> `self`
    - `Source` / `File` -> `self.plugin`
    - `Show` / `Season` / `Episode` -> the joined `Plugin`
    """

    @abstractmethod
    def _root_record(self, session: Session) -> _RootRecord:
        """Return the record that owns `user_id` and `visibility`."""

    def get_user_id(self, session: Session) -> uuid.UUID:
        """Return the `id` of the `User` who owns this record."""
        return self._root_record(session).user_id

    def is_public(self, session: Session) -> bool:
        """Return whether this record's `visibility` is `public`."""
        return self._root_record(session).visibility == Visibility.public

    def is_publically_readable(self, session: Session) -> bool:
        """Return whether this record's `visibility` is `public` or `unlisted`."""
        return self._root_record(session).visibility in (
            Visibility.public,
            Visibility.unlisted,
        )


if TYPE_CHECKING:
    from sqlalchemy import Table
    from sqlalchemy.orm._typing import OrmExecuteOptionsParameter
    from sqlalchemy.orm.interfaces import ORMOption
    from sqlalchemy.sql.selectable import ForUpdateParameter

    from app.episodes.models import Episode
    from app.plugins.models import File, Plugin
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source
    from app.users.models import User


# Partial function because it reduces the number of locations that need to
# have a "# type: ignore[call-overload]" comment. Ignoring this error is acceptable
# because the official example for implementing a DateTime field also ignore the error:
# https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/models.py
DateTimeField = partial(Field, sa_type=DateTime(timezone=True))  # type: ignore[call-overload]


class TimestampIdAndHashMixin(SQLModel):
    """Mixin used for most models.

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

    def __hash__(self) -> int:
        """Return a hash representation of the record based on the `id`."""
        return hash(self.id)


class BaseMediaMixin(SQLModel):
    """Mixin for base media models.

    Used for `BasePlugin`, `BaseSource`, `BaseShow`, `BaseSeason`, and
    `BaseEpisode` models.
    """

    # key is a surrogate key so the name key makes it easier to differentiate between
    # the key field and the id field.
    key: str = Field(min_length=1)
    data_timestamp: datetime | None = DateTimeField(default=None)
    update_at: datetime | None = DateTimeField(default=None)
    deleted_at: datetime | None = DateTimeField(default=None)

    # Allows plugins to store custom information beyond the database's structure.
    extra: str | None = Field(default=None)


class MediaMixin[
    ParentT: User | Plugin | Source | Show | Season,
    ChildT: Plugin | Source | Show | Season | Episode | File,
](TimestampIdAndHashMixin, BaseMediaMixin, RootRecordMixin, ABC):
    """Mixin for media models.

    Used for `Plugin`, `Source`, `Show`, `Season`, and `Episode` models.
    """

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

    def set_update_at(self, new_update_at_value: datetime | None) -> None:
        """Set `update_at` based its current value and `new_update_at_value`."""
        # If the existing update_at is older than data_timestamp the update has
        # been completed and update_at can be cleared.
        if (
            self.update_at
            and self.data_timestamp
            and self.update_at < self.data_timestamp
        ):
            self.update_at = None

        if not new_update_at_value:
            return

        # If the existing data_timestamp is newer than the new update_at value update_at
        # can be ignored because the data is already up to date.
        if self.data_timestamp and self.data_timestamp >= new_update_at_value:
            return

        # If the new update_at happens before the existing update_at the existing
        # update_at should be replaced so the updates occur as soon as possible.
        if self.update_at is None or new_update_at_value < self.update_at:
            self.update_at = new_update_at_value

    def add_child(self, child: ChildT) -> None:
        """Add a child to the record."""
        self.children.append(child)

    # Will be automatically set when table=True, required for type checking
    # parent_id_field.
    # TODO: Maybe remove this and explicitly check the value.
    __table__: ClassVar[Table]

    @classmethod
    def parent_id_field(cls) -> str:
        """Return the name of the parent id column.

        Raises:
            ValueError: If there are not exactly 1 foreign key columns on the model.

        """
        foreign_key_columns: list[str] = [
            column.name for column in cls.__table__.columns if column.foreign_keys
        ]
        if len(foreign_key_columns) != 1:
            msg = (
                f"Expected exactly 1 foreign key column on {cls.__name__}, "
                f"found {len(foreign_key_columns)}: {foreign_key_columns}"
            )
            raise ValueError(msg)
        return foreign_key_columns[0]

    def set_parent_id(self, parent_id: uuid.UUID) -> None:
        """Set the parent id key on the record."""
        setattr(self, type(self).parent_id_field(), parent_id)

    # TODO: Consider implementing a recursive version of this so only one upsert needs
    # to be called when upserting a tree of records.
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
            # update_at: set manually with set_update_at.
            # created_at: set by the database.
            # modified_at: set by the database.
            protected_keys.update({"id", "update_at", "created_at", "modified_at"})
            dumped = self.model_dump(exclude=protected_keys)
            existing_record.sqlmodel_update(dumped)
            existing_record.set_update_at(self.update_at)
            return existing_record
        # self will always be a child of parent
        parent.add_child(self)  # type: ignore[arg-type]
        return self

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

    def soft_delete_missing_children(self, expected_keys: Iterable[str]) -> None:
        """Soft delete children whose keys are not in `expected_keys`."""
        expected = set(expected_keys)
        for child in self.children:
            if child.key not in expected:
                child.soft_delete()
