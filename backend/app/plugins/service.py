# TODO: Validate
from fastapi import HTTPException
from sqlmodel import Session

from app.plugins.schemas import (
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginSearchInformation,
    PluginSearchUrl,
    PluginURLMatch,
)
from plugins.utils.abstract_plugin import (
    AbstractPlugin,
    PluginMediaInfo,
    PluginSearchResults,
)
from plugins.utils.manage_plugins import sorted_plugins


# TODO: Validate
def _plugin_supporting(
    plugin_key: str,
    capability: str,
    refusal: str,
) -> AbstractPlugin:
    """Return the plugin `plugin_key` names, refusing one that cannot do `capability`."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.implements(capability):
                raise HTTPException(status_code=422, detail=refusal)
            return plugin_cls
    raise HTTPException(
        status_code=404,
        detail=f"Plugin {plugin_key!r} not found.",
    )


# TODO: Validate
def import_watch_history_information() -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    return [
        PluginImportWatchHistoryInformation(
            plugin_key=plugin_cls.plugin_key(),
            file_extension=plugin_cls.import_watch_history_file_extension,
            instructions=plugin_cls.import_watch_history_instructions(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("import_watch_history")
    ]


# TODO: Validate
def import_url_information() -> list[PluginImportURLInformation]:
    """Return information about the plugins offered as ways to add by URL.

    A plugin that imports URLs but is only reached through another one is left
    out. `match-url` still resolves its URLs, so one a `User` pastes anyway is
    imported rather than rejected.
    """
    return [
        PluginImportURLInformation(
            name=plugin_cls.plugin_key(),
            instructions=plugin_cls.import_url_instructions(),
            favicon_url=plugin_cls.favicon_url(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("import_url")
    ]


# TODO: Validate
def match_url(url: str) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.implements("import_url") and plugin_cls.is_valid_url_format(url):
            return PluginURLMatch(matched=True, plugin_key=plugin_cls.plugin_key())
    return PluginURLMatch(matched=False)


# TODO: Validate
def search_information() -> list[PluginSearchInformation]:
    """Return every plugin a `User` may search, in-app ones ahead of manual ones."""
    return [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
            favicon_url=plugin_cls.favicon_url(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("in_app_search")
    ] + [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
            manual_search_only=True,
            favicon_url=plugin_cls.favicon_url(),
        )
        for plugin_cls in sorted_plugins()
        if not plugin_cls.implements("in_app_search")
        and plugin_cls.implements("manual_search")
    ]


# TODO: Validate
def manual_search(plugin_key: str, query: str) -> PluginSearchUrl:
    """Return a plugin website's own search-page URL for `query`."""
    plugin_cls = _plugin_supporting(
        plugin_key,
        "manual_search",
        f"Plugin {plugin_key!r} cannot be searched.",
    )
    return PluginSearchUrl(url=plugin_cls.manual_search(query))


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
