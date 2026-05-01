"""Source dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import owned_record, readable_record
from app.sources.models import Source

ReadableSource = Annotated[Source, Depends(readable_record(Source, "source_id"))]
OwnedSource = Annotated[Source, Depends(owned_record(Source, "source_id"))]
