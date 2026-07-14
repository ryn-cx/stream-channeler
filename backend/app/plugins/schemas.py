# TODO: Validate
"""Plugin schemas."""
import uuid

from pydantic import BaseModel

from app.plugins.models import BasePlugin, Plugin
from app.schemas import (
    BaseCreateWithParentAndKey,
    BaseUpdateWithKey,
    make_model_with_all_fields_optional,
)
from app.users.models import User


class PluginCreate(BaseCreateWithParentAndKey[Plugin, User], BasePlugin):
    """Schema for creating a `Plugin`."""


class PluginUpdate(
    make_model_with_all_fields_optional(BasePlugin),
    BaseUpdateWithKey[Plugin],
):
    """Schema for updating a `Plugin`."""


class PluginOutput(BasePlugin):
    """Schema for returning a `Plugin`."""

    id: uuid.UUID


class PluginsPublic(BaseModel):
    """Schema for returning a list of `Plugin`s."""

    data: list[PluginOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


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
