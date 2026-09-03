# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.plugins import service
from app.plugins.schemas import (
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginSearchInformation,
    PluginSearchUrl,
    PluginURLMatch,
)
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginSearchResults

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


# TODO: Validate
@plugins_router.get("/import-watch-history-information")
def import_watch_history_information(
    _current_user: CurrentUser,
) -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    return service.import_watch_history_information()


# TODO: Validate
@plugins_router.get("/import-url-information")
def import_url_information(
    _current_user: CurrentUser,
) -> list[PluginImportURLInformation]:
    """Return information about the plugins offered as ways to add by URL."""
    return service.import_url_information()


# TODO: Validate
@plugins_router.get("/match-url")
def match_url(url: str, _current_user: CurrentUser) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    return service.match_url(url)


# TODO: Validate
@plugins_router.get("/search-information")
def search_information(_current_user: CurrentUser) -> list[PluginSearchInformation]:
    """Return every plugin a `User` may search."""
    return service.search_information()


# TODO: Validate
@plugins_router.get("/manual-search")
def manual_search(
    plugin_key: str,
    query: str,
    _current_user: CurrentUser,
) -> PluginSearchUrl:
    """Return a plugin website's own search-page URL for `query`."""
    return service.manual_search(plugin_key, query)


# TODO: Validate
@plugins_router.get("/in-app-search")
def in_app_search(
    plugin_key: str,
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
    cursor: str | None = None,
) -> PluginSearchResults:
    """Search for shows/movies on a plugin's platform.

    `cursor` is the `next_cursor` of an earlier page; omit it for the first one.
    """
    return service.in_app_search(session, plugin_key, query, cursor)


# TODO: Validate
@plugins_router.get("/media-info")
def media_info(
    plugin_key: str,
    media_identifier: str,
    session: SessionDep,
    _current_user: CurrentUser,
) -> PluginMediaInfo | None:
    """Return everything a plugin knows about one of its own search results."""
    return service.media_info(session, plugin_key, media_identifier)


router = APIRouter()
router.include_router(plugins_router)
