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
    """Schema for returning one shelved title."""

    id: uuid.UUID
    name: str | None
    year: int | None
    poster_url: str | None
    poster_thumbnail_url: str | None
    thumbnail_url: str | None
    image_url: str | None
    description: str | None
    genres: list[str]
    url: str | None
    season_count: int
    episode_count: int


# TODO: Validate
class VideoStoreTitlesOutput(BaseModel):
    """Schema for returning a page of a `Source`'s shelved titles."""

    titles: list[VideoStoreTitleOutput]
    total: int
