# TODO: Validate
"""Source dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import existing_record
from app.sources.models import Source

ExistingSource = Annotated[Source, Depends(existing_record(Source, "source_id"))]
