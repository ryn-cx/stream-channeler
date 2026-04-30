# TODO: Validate
import uuid

from sqlmodel import Field

from app.schemas import BasePatchInputWithKey, BaseCreateWithChild
from app.shows.models import BaseShow, Show
from app.sources.models import Source


class ShowCreate(BaseCreateWithChild[Show, Source], BaseShow):
    pass


class ShowUpdate(BasePatchInputWithKey[Show], BaseShow):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.


class ShowPublic(BaseShow):
    source_id: uuid.UUID
    id: uuid.UUID
