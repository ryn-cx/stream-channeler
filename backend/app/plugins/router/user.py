# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.plugins.schemas import (
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginSearchResults,
    PluginURLMatch,
    TMDBMediaInfo,
)
from app.plugins.service import imports, search

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


# TODO: Validate
@plugins_router.get("/import-watch-history-information")
def import_watch_history_information(
    _current_user: CurrentUser,
) -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    return imports.import_watch_history_information()


# TODO: Validate
@plugins_router.get("/import-url-information")
def import_url_information(
    _current_user: CurrentUser,
) -> list[PluginImportURLInformation]:
    """Return information about the plugins offered as ways to add by URL."""
    return imports.import_url_information()


# TODO: Validate
@plugins_router.get("/match-url")
def match_url(url: str, _current_user: CurrentUser) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    return imports.match_url(url)


# TODO: Validate
@plugins_router.get("/in-app-search")
def in_app_search(
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
    cursor: str | None = None,
) -> PluginSearchResults:
    """`cursor` is the `next_cursor` of an earlier page; omit it for the first one."""
    return search.in_app_search(session, query, cursor)


# TODO: Validate
@plugins_router.get("/media-info")
def media_info(
    media_identifier: str,
    session: SessionDep,
    _current_user: CurrentUser,
) -> TMDBMediaInfo:
    """Return everything TMDB knows about one of its own search results."""
    return search.media_info(session, media_identifier)


router = APIRouter()
router.include_router(plugins_router)
