# TODO: Validate
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


# TODO: Validate
class UnmatchedSourceOutput(BaseModel):
    id: uuid.UUID
    provider_name: str
    plugin_key: str | None
    created_at: datetime
    modified_at: datetime
    show_id: uuid.UUID
    show_name: str | None


# TODO: Validate
class UnmatchedSourceImport(BaseModel):
    url: str = Field(min_length=1)
