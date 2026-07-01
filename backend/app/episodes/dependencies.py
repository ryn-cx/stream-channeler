"""Episode dependencies."""

from typing import Annotated

from fastapi import Depends

from app.episodes.models import Episode
from app.media.service import editable_record, readable_record

ReadableEpisode = Annotated[Episode, Depends(readable_record(Episode, "episode_id"))]
EditableEpisode = Annotated[Episode, Depends(editable_record(Episode, "episode_id"))]
