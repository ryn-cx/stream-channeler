"""Watch dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record
from app.watches.models import Watch

EditableWatch = Annotated[Watch, Depends(editable_record(Watch, "watch_id"))]
