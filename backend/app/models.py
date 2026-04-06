# TODO: Validate
from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from functools import partial
from typing import TYPE_CHECKING, Self

from sqlmodel import DateTime, Field, SQLModel

from app.utils import tz_datetime

if TYPE_CHECKING:
    from app.channels.models import Channel
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
    """Mixin that adds created_at, modified_at, and id fields and a hash function."""

    # Named id because uuid already contains the word id inside of it, making it easier
    # to differentiate between the id field and the key field.
    id: uuid.UUID = Field(unique=True, default_factory=uuid.uuid4)

    created_at: datetime = DateTimeField(default_factory=tz_datetime.now)
    modified_at: datetime = DateTimeField(
        sa_column_kwargs={"onupdate": tz_datetime.now},
        default_factory=tz_datetime.now,
    )

    def __hash__(self) -> int:
        return hash(self.id)


class BaseMediaMixin(SQLModel):
    """Mixin for base media models.

    Used for ``BasePlugin``, ``BaseSource``, ``BaseShow``, ``BaseSeason``, and
    ``BaseEpisode`` models.

    Adds data_timestamp update_at, deleted_at, and extra fields and a set_update_at
    function."""

    # Named key because it is a surrogate key, making it easier to differentiate between
    # the id field and the key field.
    key: str
    data_timestamp: datetime | None = DateTimeField(default=None)
    update_at: datetime | None = DateTimeField(default=None)
    deleted_at: datetime | None = DateTimeField(default=None)

    # Allows plugins to store custom information beyond the database's structure.
    extra: str | None = Field(default=None)


class MediaMixin[
    ParentT: User | Plugin | Source | Show | Season,
    ChildT: Channel | Plugin | Source | Show | Season | Episode | File,
](TimestampIdAndHashMixin, BaseMediaMixin, ABC):
    """Mixin for media models.

    Used for ``Plugin``, ``Source``, ``Show``, ``Season``, and ``Episode`` models.
    """

    @abstractmethod
    def parent(self) -> ParentT:
        """Return the parent of the entry."""

    def set_update_at(self, update_at: datetime | None) -> None:
        """Set ``update_at`` to the earliest useful time, clearing stale values."""
        # If the existing update_at is newer than the existing data_timestamp update_at
        # can be cleared because the update has been completed.
        if (
            self.update_at
            and self.data_timestamp
            and self.update_at < self.data_timestamp
        ):
            self.update_at = None

        if not update_at:
            return

        # If the existing data_timestamp is newer than the new update_at value update_at
        # can be ignored because the data is already up to date.
        if self.data_timestamp and self.data_timestamp >= update_at:
            return

        # If the new update_at happens before the existing update_at the existing
        # update_at should be replaced so the updates occur as soon as possible.
        if self.update_at is None or update_at < self.update_at:
            self.update_at = update_at

    def add_child(self, child: ChildT) -> None:
        self.children().append(child)

    def upsert(
        self,
        parent: ParentT,
        existing_entry: Self | None,
        protected_keys: set[str] | None = None,
    ) -> Self:
        if protected_keys is None:
            protected_keys = set()
        if existing_entry:
            # id is automatically generated when making a model, but that value should
            # only be used for new entries. When updating the original id should be
            # preserved.
            # update_at is set manually with set_update_at.
            # created_at and modified_at are set by the database.
            protected_keys.update({"id", "update_at", "created_at", "modified_at"})
            dumped = self.model_dump(exclude=protected_keys)
            existing_entry.sqlmodel_update(dumped)
            existing_entry.set_update_at(self.update_at)
            return existing_entry
        # TODO: Is there a good way to type hint this?
        parent.add_child(self)  # type: ignore[arg-type]
        return self

    def children(self) -> list[ChildT]:
        """Return the direct children of the entry.

        Parent list
        - ``Plugin`` -> ``Source | Files``
        - ``Source`` -> ``Show``
        - ``Show`` -> ``Season``
        - ``Season`` -> ``Episode``
        """
        # Default value used by episodes because episodes have no children.
        return []

    def soft_delete(
        self,
        timestamp: datetime | None = None,
        *,
        recursive: bool = True,
    ) -> None:
        """Soft delete the entry.

        If it has already been deleted, the existing deleted_at value will be kept.
        """
        if self.deleted_at is None:
            self.deleted_at = timestamp or tz_datetime.now()

        if recursive:
            for child in self.children():
                child.soft_delete(timestamp)

    def soft_undelete(self, *, recursive: bool = True) -> None:
        """Soft undelete the entry."""
        self.deleted_at = None
        if recursive:
            for child in self.children():
                child.soft_undelete()

    def soft_delete_missing_children(
        self,
        keys: list[str] | set[str],
        *,
        recursive: bool = True,
    ) -> None:
        """Soft-delete all children whose key is not in keys."""
        if isinstance(keys, list):
            keys = set(keys)

        for child in self.children():
            if child.key not in keys and child.deleted_at is None:
                child.soft_delete(recursive=recursive)

    def soft_undelete_found_children(
        self,
        keys: list[str] | set[str],
        *,
        recursive: bool = True,
    ) -> None:
        """Soft-undelete all children whose key is in keys."""
        if isinstance(keys, list):
            keys = set(keys)

        for child in self.children():
            if child.key in keys and child.deleted_at is not None:
                child.soft_undelete(recursive=recursive)
