# TODO: Validate
"""Plugin schemas."""

import uuid

from fastapi import HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.plugins.models import BasePlugin, Plugin
from app.schemas import (
    BaseInput,
    make_model_with_all_fields_optional,
)


# TODO: Validate
class PluginCreate(BaseInput, BasePlugin):
    """Schema for creating a `Plugin`."""

    # TODO: Validate
    def create(self, session: Session) -> Plugin:
        if Plugin.get(session, self.key):
            raise HTTPException(
                status_code=409,
                detail="Plugin with this key already exists",
            )
        plugin = Plugin.model_validate(self)
        session.add(plugin)
        session.commit()
        session.refresh(plugin)
        return plugin


# TODO: Validate
class PluginUpdate(
    make_model_with_all_fields_optional(BasePlugin),
    BaseInput,
):
    """Schema for updating a `Plugin`."""

    # TODO: Validate
    def update(self, session: Session, existing_record: Plugin) -> Plugin:
        if (
            self.key is not None
            and self.key != existing_record.key
            and Plugin.get(session, self.key)
        ):
            raise HTTPException(
                status_code=409,
                detail="Plugin with this key already exists",
            )

        existing_record.sqlmodel_update(self.model_dump(exclude_unset=True))
        session.commit()
        return existing_record


# TODO: Validate
class PluginOutput(BasePlugin):
    """Schema for returning a `Plugin`."""

    id: uuid.UUID


# TODO: Validate
class PluginListOutput(PluginOutput):
    """Schema for returning a list of `Plugin`s."""


# TODO: Validate
class PluginsPublic(BaseModel):
    """Schema for returning a list of `Plugin`s."""

    data: list[PluginListOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool


# TODO: Validate
class PluginImportWatchHistoryInformation(BaseModel):
    plugin_key: str
    file_extension: str
    instructions: str


# TODO: Validate
class PluginImportURLInformation(BaseModel):
    name: str
    instructions: str
    favicon_url: str | None = None


# TODO: Validate
class PluginSearchInformation(BaseModel):
    plugin_key: str
    name: str
    manual_search_only: bool = False
    favicon_url: str | None = None


# TODO: Validate
class PluginURLMatch(BaseModel):
    matched: bool
    plugin_key: str | None = None


# TODO: Validate
class PluginSearchUrl(BaseModel):
    url: str | None = None
