# TODO: Validate
from collections.abc import Sequence

from sqlmodel import Session

from app.plugins.schemas import (
    PluginSearchResults,
    SearchWatchProviders,
    TMDBMediaInfo,
)
from plugins.TMDB import TMDB


# TODO: Validate
def in_app_search(
    session: Session,
    query: str,
    cursor: str | None = None,
) -> PluginSearchResults:
    """`cursor` is the `next_cursor` of an earlier page; omit it for the first one."""
    return TMDB(session).in_app_search(query, cursor)


# TODO: Validate
def media_info(session: Session, media_identifier: str) -> TMDBMediaInfo:
    """Return everything TMDB knows about one of its own search results."""
    return TMDB(session).title_info(media_identifier)


# TODO: Validate
def search_watch_providers(
    session: Session,
    media_identifiers: Sequence[str],
) -> SearchWatchProviders:
    """Return the streaming services each search result can be watched on."""
    return TMDB(session).search_watch_providers(media_identifiers)
