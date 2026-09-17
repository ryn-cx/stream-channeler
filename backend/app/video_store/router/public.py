# TODO: Validate
"""Video store router."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Path, Query

from app.auth.dependencies import SessionDep
from app.sources.dependencies import ExistingSource
from app.video_store import service
from app.video_store.schemas import (
    VideoStoreRegionOutput,
    VideoStoreSourceOutput,
    VideoStoreTitlesOutput,
    VideoStoreWatchProviderOutput,
)
from app.video_store.service import STORE_TITLE_PAGE

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
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=STORE_TITLE_PAGE)] = STORE_TITLE_PAGE,
) -> VideoStoreTitlesOutput:
    """Read a page of the titles a `Source` carries."""
    return service.store_titles(session, source, offset, limit)


# TODO: Validate
@video_store_router.get("/regions")
def get_store_regions(
    session: SessionDep,
) -> list[VideoStoreRegionOutput]:
    """Read every region a watch provider store can be built for."""
    return service.store_regions(session)


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
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=STORE_TITLE_PAGE)] = STORE_TITLE_PAGE,
) -> VideoStoreTitlesOutput:
    """Read a page of the titles a `WatchProvider` offers in `region`."""
    return service.provider_titles(
        session,
        watch_provider_id,
        region.upper(),
        offset,
        limit,
    )


router = APIRouter()
router.include_router(video_store_router)
