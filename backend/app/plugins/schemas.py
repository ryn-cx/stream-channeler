# TODO: Validate
import uuid

from pydantic import BaseModel, ConfigDict
from sqlmodel import Field

from app.plugins.models import BasePlugin


class PluginOutput(BasePlugin):
    id: uuid.UUID


class PluginPostInput(BasePlugin):
    model_config = ConfigDict(extra="forbid")  # type: ignore[reportAssignmentType]
    # Simplify the process of creating custom media by automatically making a key for
    # the user.
    key: str = Field(default_factory=lambda: str(uuid.uuid4()))


class PluginPatchInput(BasePlugin):
    model_config = ConfigDict(extra="forbid")  # type: ignore[reportAssignmentType]
    key: str | None = Field(default=None)  # type: ignore[assignment]
    public: bool | None = Field(default=None)  # type: ignore[assignment]


class PluginImportWatchHistoryInfo(BaseModel):
    plugin_key: str
    # TODO: Can probably be changed to be required.
    file_extension: str | None = None
    instructions: str


class PluginImportURLInfo(BaseModel):
    name: str
    instructions: str


class PluginSearchInfo(BaseModel):
    plugin_key: str
    name: str
