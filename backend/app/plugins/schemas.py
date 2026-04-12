import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.plugins.models import BasePlugin, Plugin
from app.schemas import BaseInput, BasePatchInputWithKey


class PluginOutput(BasePlugin):
    id: uuid.UUID


class PluginPostInput(BaseInput, BasePlugin):
    pass


class PluginPatchInput(BasePatchInputWithKey[Plugin], BasePlugin):
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment] # Patch input can ignore required values.
    public: bool | None = Field(default=None)  # type: ignore[assignment]


class PluginImportWatchHistoryInformation(BaseModel):
    plugin_key: str
    file_extension: str
    instructions: str


class PluginImportURLInformation(BaseModel):
    name: str
    instructions: str


class PluginSearchInformation(BaseModel):
    plugin_key: str
    name: str
