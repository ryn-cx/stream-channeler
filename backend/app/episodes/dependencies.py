# TODO: Validate
"""Episode dependencies."""

from typing import Annotated

from fastapi import Depends

from app.episodes.models import Episode
from app.media.service import owned_record, readable_record

ReadableEpisode = Annotated[Episode, Depends(readable_record(Episode, "episode_id"))]
OwnedEpisode = Annotated[Episode, Depends(owned_record(Episode, "episode_id"))]
