# TODO: Validate
"""Season dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import owned_record, readable_record
from app.seasons.models import Season

ReadableSeason = Annotated[Season, Depends(readable_record(Season, "season_id"))]
OwnedSeason = Annotated[Season, Depends(owned_record(Season, "season_id"))]
