# TODO: Validate
import uuid

from pydantic import ConfigDict
from sqlmodel import Field

from app.seasons.models import BaseSeason


class SeasonOutput(BaseSeason):
    show_id: uuid.UUID
    id: uuid.UUID


class SeasonPostInput(BaseSeason):
    model_config = ConfigDict(extra="forbid")  # type: ignore[reportAssignmentType]
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class SeasonPatchInput(BaseSeason):
    model_config = ConfigDict(extra="forbid")  # type: ignore[reportAssignmentType]
    key: str | None = Field(default=None)  # type: ignore[assignment]
