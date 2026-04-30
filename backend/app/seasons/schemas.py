# TODO: Validate
import uuid

from sqlmodel import Field

from app.schemas import BasePatchInputWithKey, BaseCreateWithChild
from app.seasons.models import BaseSeason, Season
from app.shows.models import Show


class SeasonOutput(BaseSeason):
    show_id: uuid.UUID
    id: uuid.UUID


class SeasonPostInput(BaseCreateWithChild[Season, Show], BaseSeason):
    pass


class SeasonPatchInput(BasePatchInputWithKey[Season], BaseSeason):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.
