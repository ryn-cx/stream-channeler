# TODO: Validate
import uuid

from pydantic import ConfigDict
from sqlmodel import Field

from app.episodes.models import BaseEpisode


class EpisodeOutput(BaseEpisode):
    id: uuid.UUID
    season_id: uuid.UUID


class EpisodePostInput(BaseEpisode):
    model_config = ConfigDict(extra="forbid")  # type: ignore[reportAssignmentType]
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class EpisodePatchInput(BaseEpisode):
    model_config = ConfigDict(extra="forbid")  # type: ignore[reportAssignmentType]
    # assignment - Patch input can ignore required values.
    key: str | None = Field(default=None)  # type: ignore[assignment]
