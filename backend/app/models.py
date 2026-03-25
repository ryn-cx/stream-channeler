from __future__ import annotations

import uuid
from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import DateTime, Field, SQLModel

from app.users.models import User
from app.utils import tz_datetime

if TYPE_CHECKING:
    from app.episodes.models import Episode
    from app.plugins.models import Plugin
    from app.seasons.models import Season
    from app.shows.models import Show
    from app.sources.models import Source


SA_TYPE = DateTime(timezone=True)


# Generic message
class Message(SQLModel):
    message: str


class TimestampAndIdMixin(SQLModel):
    """Mixin to add created_at, modified_at and id fields to the model."""

    id: uuid.UUID = Field(unique=True, default_factory=uuid.uuid4)

    # This is basically the same as the "official" example of how to implement a
    # created_at timestamp as seen here:
    # https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/models.py
    # call-overload - From the original template
    created_at: datetime = Field(sa_type=SA_TYPE, default_factory=tz_datetime.now)  # type: ignore[call-overload]

    # This is basically the same as the implementation of created_at, but it includes
    # the addition of an onupdate to automatically update the timestamp when the record
    # is modified.
    modified_at: datetime = Field(
        sa_type=SA_TYPE,  # type: ignore[call-overload]
        sa_column_kwargs={"onupdate": tz_datetime.now},
        default_factory=tz_datetime.now,
    )

    def __hash__(self) -> int:
        return hash(self.id)


class BaseMediaMixin(SQLModel):
    """Base mixin for media models (Plugin/Source/Show/Season/Episode).

    Mixin to add data_timestamp update_at, deleted_at, and extra fields to the model."""

    key: str
    data_timestamp: datetime | None = Field(sa_type=SA_TYPE, default=None)  #  type: ignore[call-overload]
    update_at: datetime | None = Field(sa_type=SA_TYPE, default=None)  # type: ignore[call-overload]
    deleted_at: datetime | None = Field(sa_type=SA_TYPE, default=None)  # type: ignore[call-overload]

    # This is an optional field that can store anything that does not fit in the other
    # available fields. It will only ever be used by custom plugins, and allows them to
    # store extra information without needing to modify the database schema.
    extra: str | None = Field(default=None)

    def set_update_at(self, update_at: datetime | None) -> None:
        """Validate and set the update_at field.

        If the existing value is in the future, only allow decrementing. This will make
        updates occur as soon as possible. If the existing value is in the past, only
        allow incrementing. This will make sure an older update_at value does not cause
        updates to skip by overwriting a newer value.
        For example
        - Current date is January 4th
        - data_timestamp is January 2nd
        - update_at is January 3rd
        - new update_at is set to January 1st
        The data from January 3rd will be lost in this situation.

        , and if it is in
        the past, only allow incrementing. Only decrementing makes it so files are
        updated as soon as possible, and only incrementing makes it so files don't
        accidently use old data.
        """
        if not update_at:
            return

        if self.update_at is None:
            self.update_at = update_at
            return

        now = datetime.now(tz=self.update_at.tzinfo)

        if (self.update_at > now and update_at < self.update_at) or (
            self.update_at <= now and update_at > self.update_at
        ):
            self.update_at = update_at


class MediaMixin(TimestampAndIdMixin, BaseMediaMixin, ABC):
    """Main mixin for media models (Plugin/Source/Show/Season/Episode)."""

    def children(self) -> list[Source] | list[Show] | list[Season] | list[Episode]:
        """Return the direct children of the entry.

        Parent list: Plugin > Source > Show > Season > Episode

        Files are intentionally excluded from the children because they are not part of
        the direct media hierarchy.

        This is used for all recursive operations.
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

    def soft_delete_missing_children(self, valid_keys: list[str] | set[str]) -> None:
        """Soft-delete children if their key is not in valid_keys."""
        if isinstance(valid_keys, list):
            valid_keys = set(valid_keys)

        for child in self.children():
            if child.key not in valid_keys and child.deleted_at is None:
                child.soft_delete()

    def soft_undelete(self, *, recursive: bool = True) -> None:
        """Soft undelete the entry."""
        self.deleted_at = None
        if recursive:
            for child in self.children():
                child.soft_undelete()

    def parent(self) -> Plugin | Source | Show | Season | User | None:
        """Return the parent of the entry."""
        # Default to having no parent and let subclasses override this method.
        return None


class BaseInputMixin[T: BaseMediaMixin](BaseMediaMixin):
    def _update_existing_entry(
        self,
        existing_entry: T,
        protected_keys: set[str],
    ) -> T:
        # This function will never directly set update_at to None because it is possible
        # that update_at is None because the value was not defined. However, the call to
        # set_update_at can set the value to None if the data_timestamp is newer than
        # the existing update_at value.

        # Never upsert the update_at value because it will be managed by the
        # set_update_at method which has additional logic to validate and set the value.
        protected_keys.add("update_at")

        dumped = self.model_dump(exclude=protected_keys)
        existing_entry.sqlmodel_update(dumped)
        existing_entry.set_update_at(self.update_at)
        return existing_entry

    def clean_protected_keys(
        self,
        protected_keys: set[str] | None,
    ) -> set[str]:
        if protected_keys is None:
            return set()
        return protected_keys
