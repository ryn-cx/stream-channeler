# TODO: Validate
"""Video store schemas."""

import uuid

from pydantic import BaseModel


# TODO: Validate
class VideoStoreSourceOutput(BaseModel):
    """Schema for returning a `Source` a store can be built from."""

    id: uuid.UUID
    key: str
    plugin_name: str
    favicon_url: str | None
    image_url: str | None
    title_count: int


# TODO: Validate
class VideoStoreRegionOutput(BaseModel):
    """Schema for returning a region titles can be shelved by."""

    region: str
    title_count: int


# TODO: Validate
class VideoStoreWatchProviderOutput(BaseModel):
    """Schema for returning a `WatchProvider` a store can be built from."""

    id: uuid.UUID
    tmdb_provider_id: int
    name: str
    logo_url: str | None
    title_count: int


# TODO: Validate
class VideoStoreTitleOutput(BaseModel):
    """Schema for returning one shelved title, as its case on the shelf."""

    id: uuid.UUID
    name: str | None
    year: int | None
    score: float | None
    popularity: float | None
    media_type: str | None
    original_language: str | None
    languages: list[str]
    thumbnail_url: str | None
    is_poster: bool
    genres: list[str]
    season_count: int
    episode_count: int


# TODO: Validate
class VideoStoreLanguageOutput(BaseModel):
    """Schema for returning one language titles can be filtered by."""

    code: str
    name: str | None
    title_count: int


# TODO: Validate
class VideoStoreTitleDetailOutput(BaseModel):
    """Schema for returning everything a title's case viewer shows."""

    id: uuid.UUID
    name: str | None
    year: int | None
    poster_url: str | None
    image_url: str | None
    description: str | None
    original_language: str | None
    languages: list[str]
    url: str | None


# TODO: Validate
class VideoStoreTitlesOutput(BaseModel):
    """Schema for returning every title a store shelves."""

    titles: list[VideoStoreTitleOutput]
