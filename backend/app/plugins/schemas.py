"""Plugin schemas."""

# TODO: Validate
import uuid

from pydantic import BaseModel
from sqlmodel import Field

from app.models import Visibility
from app.plugins.models import BasePlugin, Plugin
from app.schemas import BaseCreateWithParentAndKey, BaseUpdateWithKey
from app.users.models import User


class PluginCreate(BaseCreateWithParentAndKey[Plugin, User], BasePlugin):
    """Schema for creating a `Plugin`."""


class PluginUpdate(BaseUpdateWithKey[Plugin], BasePlugin):
    """Schema for updating a `Plugin`."""

    # Update requests use PATCH endpoints so all required fields must be made optional.
    key: str | None = Field(default=None, min_length=1)  # type: ignore[assignment]
    visibility: Visibility | None = Field(default=None)  # type: ignore[assignment]


class PluginOutput(BasePlugin):
    """Schema for returning a `Plugin`."""

    id: uuid.UUID


class PluginTableOutput(BaseModel):
    """Schema for returning a list of `Plugin`s."""

    data: list[PluginOutput]
    count: int
    server_side: bool


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


class PluginURLMatch(BaseModel):
    matched: bool
    plugin_key: str | None = None
