# TODO: Validate
"""Source dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record, readable_record
from app.sources.models import Source

ReadableSource = Annotated[Source, Depends(readable_record(Source, "source_id"))]
EditableSource = Annotated[Source, Depends(editable_record(Source, "source_id"))]
