# TODO: Validate
"""Plugin schemas."""

import uuid

from pydantic import AliasPath, BaseModel, ConfigDict, Field

from app.media.media_type import MediaType
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


# TODO: Consider reworking this into seperate models for each parent.
class PluginListOutput(PluginOutput):
    """Schema for returning a list of `Plugin`s, with owner information."""

    model_config = ConfigDict(validate_by_name=True, validate_by_alias=True)  # type: ignore[assignment]

    username: str | None = Field(validation_alias=AliasPath("user", "username"))


class PluginsPublic(BaseModel):
    """Schema for returning a list of `Plugin`s."""

    data: list[PluginListOutput]
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
    favicon_url: str | None = None


class PluginSearchInformation(BaseModel):
    plugin_key: str
    name: str
    manual_search_only: bool = False
    favicon_url: str | None = None


class PluginURLMatch(BaseModel):
    matched: bool
    plugin_key: str | None = None


class PluginSearchUrl(BaseModel):
    url: str | None = None


class TMDBMatch(BaseModel):
    """The TMDB title that best matches a plugin's search result."""

    tmdb_id: int
    media_type: MediaType


class TMDBWatchProviderItem(BaseModel):
    """A place to watch a title, marked with the plugin that supports it."""

    name: str
    icon_url: str | None = None
    plugin_key: str | None = None
    search_url: str | None = None


class TMDBMediaInfo(BaseModel):
    """Rich detail for a single movie or TV show plus its US watch providers."""

    title: str | None = None
    tagline: str | None = None
    overview: str | None = None
    poster_url: str | None = None
    backdrop_url: str | None = None
    year: int | None = None
    end_year: int | None = None
    status: str | None = None
    rating: float | None = None
    vote_count: int | None = None
    number_of_seasons: int | None = None
    number_of_episodes: int | None = None
    runtime: int | None = None
    genres: list[str] = []
    providers: list[TMDBWatchProviderItem] = []
