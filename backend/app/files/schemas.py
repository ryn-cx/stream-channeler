"""Files schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel

from app.files.models import BaseFile, File
from app.models import BaseMediaMixin, DateTimeField
from app.plugins.models import Plugin
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)


class FileCreate(BaseCreateWithParentAndKey[File, Plugin], BaseFile):
    """Schema for creating a `File`."""


class FileUpdate(
    make_model_with_all_fields_optional(BaseFile),
    BaseUpdateWithKey[File],
):
    """Schema for updating a `File`."""


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


class FilesPublic(BaseModel):
    """Schema for returning a paginated list of `File`s."""

    data: list[FileListPublic]
    total_count: int
    filtered_count: int
    is_server_side: bool
