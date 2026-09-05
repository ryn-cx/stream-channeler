# TODO: Validate
from sqlmodel import Session

from app.plugins.schemas import (
    PluginSearchInformation,
    PluginSearchUrl,
    TMDBMediaInfo,
)
from app.plugins.service.lookup import _plugin_supporting
from plugins.TMDB import TMDB
from plugins.utils.abstract_plugin import (
    PluginSearchResults,
)
from plugins.utils.manage_plugins import sorted_plugins


# TODO: Validate
def search_information() -> list[PluginSearchInformation]:
    """Return every plugin a `User` may search, in-app ones ahead of manual ones."""
    return [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_name(),
            name=plugin_cls.plugin_name(),
            favicon_url=plugin_cls.favicon_url(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("in_app_search")
    ] + [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_name(),
            name=plugin_cls.plugin_name(),
            manual_search_only=True,
            favicon_url=plugin_cls.favicon_url(),
        )
        for plugin_cls in sorted_plugins()
        if not plugin_cls.implements("in_app_search")
        and plugin_cls.implements("manual_search_url")
    ]


# TODO: Validate
def manual_search_url(plugin_key: str, query: str) -> PluginSearchUrl:
    """Return a plugin website's own search-page URL for `query`."""
    plugin_cls = _plugin_supporting(
        plugin_key,
        "manual_search_url",
        f"Plugin {plugin_key!r} cannot be searched.",
    )
    return PluginSearchUrl(url=plugin_cls.manual_search_url(query))


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
    """Return everything a plugin knows about one of its own search results."""
    return TMDB(session).media_info(media_identifier)
