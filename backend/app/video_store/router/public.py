# TODO: Validate
"""Video store router."""

import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from app.auth.dependencies import SessionDep
from app.channels.schemas import TitleCardsOutput
from app.plugins.schemas import PluginSearchResult
from app.titles.dependencies import ExistingTitle
from app.user_actions.dependencies import ActionLog
from app.user_actions.models import UserActionKind
from app.video_store import service
from app.video_store.dependencies import StoreSource
from app.video_store.schemas import (
    VideoStoreFacetsOutput,
    VideoStoreLanguageOutput,
    VideoStoreProviderTitleCardOptions,
    VideoStoreRegionOutput,
    VideoStoreSourceOutput,
    VideoStoreTitleCardOptions,
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


# TODO: Validate
@video_store_router.get("/sources/{source_id}/titles")  # noqa: FAST003
def get_store_titles(
    session: SessionDep,
    source: StoreSource,
    response: Response,
    metadata: Annotated[Literal["tmdb", "source"], Query()] = "tmdb",
) -> VideoStoreTitlesOutput:
    """Read every title a `Source` has."""
    response.headers["Cache-Control"] = "public, s-maxage=86400"
    return service.store_titles(session, source, metadata)


# TODO: Validate
@video_store_router.get("/sources/{source_id}/title-cards")  # noqa: FAST003
def get_source_title_cards(
    session: SessionDep,
    source: StoreSource,
    response: Response,
    options: Annotated[VideoStoreTitleCardOptions, Query()],
) -> TitleCardsOutput:
    now = datetime.now(UTC)
    midnight = datetime.combine(now.date() + timedelta(days=1), time(), UTC)
    seconds_left = int((midnight - now).total_seconds())
    response.headers["Cache-Control"] = f"public, s-maxage={seconds_left}"
    return service.source_title_cards(session, source, options)


# TODO: Validate
@video_store_router.get("/sources/{source_id}/title-card-facets")  # noqa: FAST003
def get_source_title_card_facets(
    session: SessionDep,
    source: StoreSource,
) -> VideoStoreFacetsOutput:
    return service.source_facets(session, source)


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
    response: Response,
    region: Annotated[str, Query(min_length=2, max_length=2)] = "US",
) -> VideoStoreTitlesOutput:
    """Read every title a `WatchProvider` offers in `region`."""
    response.headers["Cache-Control"] = "public, s-maxage=86400"
    return service.provider_titles(session, watch_provider_id, region.upper())


# TODO: Validate
@video_store_router.get("/watch-providers/{watch_provider_id}/title-cards")
def get_provider_title_cards(
    session: SessionDep,
    watch_provider_id: Annotated[uuid.UUID, Path()],
    response: Response,
    options: Annotated[VideoStoreProviderTitleCardOptions, Query()],
) -> TitleCardsOutput:
    response.headers["Cache-Control"] = "public, s-maxage=86400"
    return service.provider_title_cards(session, watch_provider_id, options)


# TODO: Validate
@video_store_router.get("/watch-providers/{watch_provider_id}/title-card-facets")
def get_provider_title_card_facets(
    session: SessionDep,
    watch_provider_id: Annotated[uuid.UUID, Path()],
    region: Annotated[str, Query(min_length=2, max_length=2)] = "US",
) -> VideoStoreFacetsOutput:
    return service.provider_facets(session, watch_provider_id, region)


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
@title_router.get("/titles/{title_id}/matches")  # noqa: FAST003
def get_title_matches(
    session: SessionDep,
    title: ExistingTitle,
    action_log: ActionLog,
) -> list[PluginSearchResult]:
    """Search TMDB with what this title's website was matched on."""
    action_log.record(UserActionKind.title_matches, title_id=title.id)
    return service.title_matches(session, title)


router = APIRouter()
router.include_router(video_store_router)
router.include_router(title_router)
