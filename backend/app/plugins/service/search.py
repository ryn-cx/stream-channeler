# TODO: Validate
from sqlmodel import Session

from app.plugins.schemas import (
    PluginSearchInformation,
    PluginSearchUrl,
)
from app.plugins.service.lookup import _plugin_supporting
from plugins.utils.abstract_plugin import (
    PluginMediaInfo,
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
    plugin_key: str,
    query: str,
    cursor: str | None = None,
) -> PluginSearchResults:
    """Search for shows/movies on a plugin's platform.

    `cursor` is the `next_cursor` of an earlier page; omit it for the first one.
    """
    plugin_cls = _plugin_supporting(
        plugin_key,
        "in_app_search",
        f"Plugin {plugin_key!r} does not support search.",
    )
    return plugin_cls(session).in_app_search(query, cursor)


# TODO: Validate
def media_info(
    session: Session,
    plugin_key: str,
    media_identifier: str,
) -> PluginMediaInfo | None:
    """Return everything a plugin knows about one of its own search results.

    Answered by the same plugin the result came from, under the identifier that
    plugin issued, so a title's detail is the source's own rather than whatever
    a search of some other service turned up.
    """
    plugin_cls = _plugin_supporting(
        plugin_key,
        "media_info",
        f"Plugin {plugin_key!r} does not support media info.",
    )
    return plugin_cls(session).media_info(media_identifier)
