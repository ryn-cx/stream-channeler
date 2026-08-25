# TODO: Validate
"""Season dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import existing_record
from app.seasons.models import Season

ExistingSeason = Annotated[Season, Depends(existing_record(Season, "season_id"))]
