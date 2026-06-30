# TODO: Validate
"""Watch dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import owned_record
from app.watches.models import Watch

OwnedWatch = Annotated[Watch, Depends(owned_record(Watch, "watch_id"))]
