"""Season dependencies."""

from typing import Annotated

from fastapi import Depends

from app.media.service import editable_record, readable_record
from app.seasons.models import Season

ReadableSeason = Annotated[Season, Depends(readable_record(Season, "season_id"))]
EditableSeason = Annotated[Season, Depends(editable_record(Season, "season_id"))]
