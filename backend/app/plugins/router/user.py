# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.plugins.schemas import (
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginSearchResults,
    PluginURLMatch,
    SearchWatchProviders,
    TMDBMediaInfo,
)
from app.plugins.service import imports, search
from app.user_actions.dependencies import ActionLog
from app.user_actions.models import UserActionKind

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


# TODO: Validate
@plugins_router.get("/import-watch-history-information")
def import_watch_history_information(
    session: SessionDep,
    _current_user: CurrentUser,
) -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    return imports.import_watch_history_information(session)


# TODO: Validate
@plugins_router.get("/import-url-information")
def import_url_information(
    session: SessionDep,
    _current_user: CurrentUser,
) -> list[PluginImportURLInformation]:
    """Return information about the plugins offered as ways to add by URL."""
    return imports.import_url_information(session)


# TODO: Validate
@plugins_router.get("/match-url")
def match_url(
    url: str,
    session: SessionDep,
    _current_user: CurrentUser,
    action_log: ActionLog,
) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    action_log.record(UserActionKind.match_url, url=url)
    return imports.match_url(session, url)


# TODO: Validate
@plugins_router.get("/in-app-search")
def in_app_search(
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
    action_log: ActionLog,
    cursor: str | None = None,
) -> PluginSearchResults:
    """`cursor` is the `next_cursor` of an earlier page; omit it for the first one."""
    action_log.record(UserActionKind.tmdb_search, query=query, cursor=cursor)
    return search.in_app_search(session, query, cursor)


# TODO: Validate
@plugins_router.get("/search-watch-providers")
def search_watch_providers(
    session: SessionDep,
    _current_user: CurrentUser,
    action_log: ActionLog,
    media_identifier: Annotated[list[str], Query()],
) -> SearchWatchProviders:
    """Return the streaming services each of `media_identifier` can be watched on."""
    action_log.record(
        UserActionKind.tmdb_watch_providers,
        media_identifier=media_identifier,
    )
    return search.search_watch_providers(session, media_identifier)


# TODO: Validate
@plugins_router.get("/media-info")
def media_info(
    media_identifier: str,
    session: SessionDep,
    _current_user: CurrentUser,
    action_log: ActionLog,
) -> TMDBMediaInfo:
    """Return everything TMDB knows about one of its own search results."""
    action_log.record(UserActionKind.tmdb_media_info, media_identifier=media_identifier)
    return search.media_info(session, media_identifier)


router = APIRouter()
router.include_router(plugins_router)
