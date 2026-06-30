# TODO: Validate
"""Files dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import owned_record, readable_record
from app.plugins.models import File

ReadableFile = Annotated[File, Depends(readable_record(File, "file_id"))]
OwnedFile = Annotated[File, Depends(owned_record(File, "file_id"))]
