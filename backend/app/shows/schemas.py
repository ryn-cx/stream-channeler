import uuid

from sqlmodel import Field

from app.schemas import BasePatchInputWithKey, BasePostInputWithChild
from app.shows.models import BaseShow, Show
from app.sources.models import Source


class ShowOutput(BaseShow):
    source_id: uuid.UUID
    id: uuid.UUID


class ShowPostInput(BasePostInputWithChild[Show, Source], BaseShow):
    pass


class ShowPatchInput(BasePatchInputWithKey[Show], BaseShow):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.
