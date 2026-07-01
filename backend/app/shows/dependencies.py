"""Show dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record, readable_record
from app.shows.models import Show

ReadableShow = Annotated[Show, Depends(readable_record(Show, "show_id"))]
EditableShow = Annotated[Show, Depends(editable_record(Show, "show_id"))]
