import uuid

from sqlmodel import Field

from app.plugins.models import Plugin
from app.schemas import BasePatchInputWithKey, BasePostInputWithChild
from app.sources.models import BaseSource, Source


class SourceOutput(BaseSource):
    plugin_id: uuid.UUID
    id: uuid.UUID


class SourcePostInput(BasePostInputWithChild[Source, Plugin], BaseSource):
    pass


class SourcePatchInput(BasePatchInputWithKey[Source], BaseSource):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.
