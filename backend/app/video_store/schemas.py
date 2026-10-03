# TODO: Validate
"""Video store schemas."""

import uuid

from pydantic import BaseModel, Field


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
    tmdb_score: float | None
    tmdb_popularity: float | None
    imdb_score: float | None
    imdb_popularity: int | None
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
class VideoStoreWatchLinkOutput(BaseModel):
    """Schema for returning one website a title can be watched on."""

    source_name: str
    url: str


# TODO: Validate
class VideoStoreTitleSourceOutput(BaseModel):
    """Schema for returning one website's row of a title, as a report target."""

    title_id: uuid.UUID
    plugin_name: str
    source_key: str
    name: str | None
    url: str | None


# TODO: Validate
class VideoStoreTrailerOutput(BaseModel):
    type: str
    name: str | None
    url: str


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
    runtime: int | None
    imdb_score: float | None
    imdb_popularity: int | None
    url: str | None
    links: list[VideoStoreWatchLinkOutput]
    sources: list[VideoStoreTitleSourceOutput]
    trailers: list[VideoStoreTrailerOutput]


# TODO: Validate
class VideoStoreTitlesOutput(BaseModel):
    """Schema for returning every title a store shelves."""

    titles: list[VideoStoreTitleOutput]


# TODO: Validate
class VideoStoreOptionOutput(BaseModel):
    name: str
    title_count: int


# TODO: Validate
class VideoStoreFacetsOutput(BaseModel):
    media_types: list[VideoStoreOptionOutput]
    genres: list[VideoStoreOptionOutput]
    original_languages: list[VideoStoreLanguageOutput]
    spoken_languages: list[VideoStoreLanguageOutput]


# TODO: Validate
class VideoStoreTitleCardOptions(BaseModel):
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=100)
    query: str | None = None
    year_from: int | None = None
    year_to: int | None = None
    tmdb_score_from: float | None = None
    tmdb_score_to: float | None = None
    tmdb_popularity_from: float | None = None
    tmdb_popularity_to: float | None = None
    imdb_score_from: float | None = None
    imdb_score_to: float | None = None
    imdb_popularity_from: int | None = None
    imdb_popularity_to: int | None = None
    media_types: list[str] = Field(default_factory=list)
    original_languages: list[str] = Field(default_factory=list)
    spoken_languages: list[str] = Field(default_factory=list)
    genres: list[str] = Field(default_factory=list)


# TODO: Validate
class VideoStoreProviderTitleCardOptions(VideoStoreTitleCardOptions):
    region: str = Field(default="US", min_length=2, max_length=2)
