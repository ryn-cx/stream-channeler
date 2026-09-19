# TODO: Validate
"""Video store router."""

import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from app.auth.dependencies import SessionDep
from app.sources.dependencies import ExistingSource
from app.titles.dependencies import ExistingTitle
from app.video_store import service
from app.video_store.schemas import (
    VideoStoreLanguageOutput,
    VideoStoreRegionOutput,
    VideoStoreSourceOutput,
    VideoStoreTitleDetailOutput,
    VideoStoreTitlesOutput,
    VideoStoreWatchProviderOutput,
)

video_store_router = APIRouter(
    prefix="/video-store",
    tags=["video-store"],
)


# TODO: Validate
@video_store_router.get("/sources")
def get_store_sources(
    session: SessionDep,
) -> list[VideoStoreSourceOutput]:
    """Read every `Source` a store can be built from."""
    return service.store_sources(session)


# FAST003 - Parameter is used by ExistingSource.
# TODO: Validate
@video_store_router.get("/sources/{source_id}/titles")  # noqa: FAST003
def get_store_titles(
    session: SessionDep,
    source: ExistingSource,
    metadata: Annotated[Literal["tmdb", "source"], Query()] = "tmdb",
) -> VideoStoreTitlesOutput:
    """Read every title a `Source` carries."""
    return service.store_titles(session, source, metadata)


# TODO: Validate
@video_store_router.get("/regions")
def get_store_regions(
    session: SessionDep,
) -> list[VideoStoreRegionOutput]:
    """Read every region a watch provider store can be built for."""
    return service.store_regions(session)


# TODO: Validate
@video_store_router.get("/original-languages")
def get_original_languages(
    session: SessionDep,
) -> list[VideoStoreLanguageOutput]:
    """Read every original language a store can be filtered by."""
    return service.store_original_languages(session)


# TODO: Validate
@video_store_router.get("/spoken-languages")
def get_spoken_languages(session: SessionDep) -> list[VideoStoreLanguageOutput]:
    """Read every spoken language a store can be filtered by."""
    return service.store_spoken_languages(session)


# TODO: Validate
@video_store_router.get("/watch-providers")
def get_store_watch_providers(
    session: SessionDep,
    region: Annotated[str, Query(min_length=2, max_length=2)] = "US",
) -> list[VideoStoreWatchProviderOutput]:
    """Read every `WatchProvider` a store can be built from in `region`."""
    return service.store_watch_providers(session, region.upper())


# TODO: Validate
@video_store_router.get("/watch-providers/{watch_provider_id}/titles")
def get_provider_titles(
    session: SessionDep,
    watch_provider_id: Annotated[uuid.UUID, Path()],
    region: Annotated[str, Query(min_length=2, max_length=2)] = "US",
) -> VideoStoreTitlesOutput:
    """Read every title a `WatchProvider` offers in `region`."""
    return service.provider_titles(session, watch_provider_id, region.upper())


title_router = APIRouter(prefix="/video-store", tags=["video-store"])


# FAST003 - Parameter is used by ExistingTitle.
# TODO: Validate
@title_router.get("/titles/{title_id}")  # noqa: FAST003
def get_title_detail(
    session: SessionDep,
    title: ExistingTitle,
    metadata: Annotated[Literal["tmdb", "source"], Query()] = "tmdb",
) -> VideoStoreTitleDetailOutput:
    """Read everything the case viewer shows for one shelved title."""
    return service.title_detail(session, title, metadata)


# FAST003 - Parameter is used by ExistingTitle.
# TODO: Validate
@title_router.get("/titles/{title_id}/image")  # noqa: FAST003
async def get_title_image(
    session: SessionDep,
    title: ExistingTitle,
    url: Annotated[str, Query()],
) -> Response:
    return await service.title_image(session, title, url)


router = APIRouter()
router.include_router(video_store_router)
router.include_router(title_router)
