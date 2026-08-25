# TODO: Validate
"""Files dependencies."""

from typing import Annotated

from fastapi import Depends

from app.files.models import File
from app.media.service import existing_record

ExistingFile = Annotated[File, Depends(existing_record(File, "file_id"))]
