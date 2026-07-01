"""Files dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record, readable_record
from app.plugins.models import File

ReadableFile = Annotated[File, Depends(readable_record(File, "file_id"))]
EditableFile = Annotated[File, Depends(editable_record(File, "file_id"))]
