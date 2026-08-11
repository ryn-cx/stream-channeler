# TODO: Validate
"""Files dependencies."""

from typing import Annotated

from fastapi import Depends

from app.files.models import File
from app.media.service import editable_record, readable_record

ReadableFile = Annotated[File, Depends(readable_record(File, "file_id"))]
EditableFile = Annotated[File, Depends(editable_record(File, "file_id"))]
