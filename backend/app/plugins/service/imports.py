# TODO: Validate

from app.plugins.schemas import (
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginURLMatch,
)
from plugins.utils.manage_plugins import sorted_plugins


# TODO: Validate
def import_watch_history_information() -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    return [
        PluginImportWatchHistoryInformation(
            plugin_key=plugin_cls.plugin_name(),
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
            name=plugin_cls.plugin_name(),
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
            return PluginURLMatch(matched=True, plugin_key=plugin_cls.plugin_name())
    return PluginURLMatch(matched=False)
