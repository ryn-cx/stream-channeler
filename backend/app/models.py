# TODO: Validate
from __future__ import annotations

import uuid
from abc import ABC
from datetime import datetime
from typing import TYPE_CHECKING

from sqlmodel import DateTime, Field, SQLModel

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


class TimestampIdMixin(SQLModel):
    """Mixin to add created_at, modified_at, and id fields to the model."""

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

    id: uuid.UUID = Field(unique=True, default_factory=uuid.uuid4)


class BaseMediaMixin(SQLModel):
    """Base mixin for media models (Plugin/Source/Show/Season/Episode).

    Mixin to add data_timestamp update_at, deleted_at, and extra fields to the model."""

    key: str
    data_timestamp: datetime | None = Field(sa_type=SA_TYPE, default=None)  #  type: ignore[call-overload]
    update_at: datetime | None = Field(sa_type=SA_TYPE, default=None)  # type: ignore[call-overload]
    deleted_at: datetime | None = Field(sa_type=SA_TYPE, default=None)  # type: ignore[call-overload]

    # This is an optional field that can store anything that does not fit in the other
    # available fields. It will only ever be used by plugins, and allows plugins to
    # store extra information without needing to modify the database schema.
    extra: str | None = Field(default=None)

    def set_update_at(self, update_at: datetime | None) -> None:
        """Validate and set the update_at field.

        Validation will make sure that the update_at field is never incremented because
        updates should occur as soon as possible and there is almost never a reason to
        delay an update further into the future.

        Even if datetime is None this will still set update_at to None is the
        data_timestamp is newer than the existing update_at value.
        """
        # If the existing update_at value is newer than the data_timestamp, it has
        # already been used and can be cleared.
        if (
            self.update_at
            and self.data_timestamp
            and self.update_at < self.data_timestamp
        ):
            self.update_at = None

        # If update_at is not set nothing else needs to be done.
        if not update_at:
            return

        # If the existing data is newer than the new update_at value then the new
        # update_at can be ignored because the data is already up to date.
        if self.data_timestamp and self.data_timestamp >= update_at:
            return

        #  If the new date is before the existing date the existing date should be
        #  updated so the update happens as soon as possible.
        if self.update_at is None or update_at < self.update_at:
            self.update_at = update_at


class MetadataMixin(TimestampIdMixin, BaseMediaMixin, ABC):
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

    def soft_undelete(self, *, recursive: bool = True) -> None:
        """Undelete the entry by setting the deleted_at value to None."""
        self.deleted_at = None
        if recursive:
            for child in self.children():
                child.soft_undelete()

    def parent(self) -> Plugin | Source | Show | Season | None:
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

        # Only update modified_at if actual content fields changed. Metadata fields
        # (key, data_timestamp, deleted_at) are excluded from change detection because
        # they are lifecycle/identity fields, not content.
        metadata_fields = {"key", "data_timestamp", "deleted_at"}
        has_changes = any(
            getattr(existing_entry, k) != v
            for k, v in dumped.items()
            if k not in metadata_fields
        )

        existing_entry.sqlmodel_update(dumped)
        existing_entry.set_update_at(self.update_at)

        if has_changes:
            existing_entry.modified_at = tz_datetime.now()

        return existing_entry

    def clean_protected_keys(
        self,
        protected_keys: set[str] | None,
    ) -> set[str]:
        if protected_keys is None:
            return set()
        return protected_keys
