# TODO: Validate
import uuid

from sqlmodel import Field

from app.plugins.models import Plugin
from app.schemas import BasePatchInputWithKey, BaseCreateWithChild
from app.sources.models import BaseSource, Source


class SourceCreate(BaseCreateWithChild[Source, Plugin], BaseSource):
    pass


class SourceUpdate(BasePatchInputWithKey[Source], BaseSource):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.


class SourcePublic(BaseSource):
    plugin_id: uuid.UUID
    id: uuid.UUID
