# TODO: Validate
"""Files schemas."""

import uuid
from datetime import datetime

from sqlmodel import Field

from app.models import BaseMediaMixin, DateTimeField
from app.plugins.models import BaseFile, File, Plugin
from app.schemas import BaseCreateWithParentAndKey, BaseUpdateWithKey


class FileCreate(BaseCreateWithParentAndKey[File, Plugin], BaseFile):
    """Schema for creating a `File`."""


class FileUpdate(BaseUpdateWithKey[File], BaseFile):
    """Schema for updating a `File`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment]
    data_timestamp: datetime | None = Field(default=None)  # type: ignore[assignment]


class FilePublic(BaseFile):
    """Schema for returning a `File`."""

    plugin_id: uuid.UUID
    id: uuid.UUID


class FileListPublic(BaseMediaMixin):
    """Schema for returning a list of `File`s, excluding `content`.

    `content` is excluded to reduce the response size.
    """

    # data_timestamp is a required field for files.
    data_timestamp: datetime = DateTimeField()  # pyright: ignore[reportIncompatibleVariableOverride]
    plugin_id: uuid.UUID
    id: uuid.UUID
