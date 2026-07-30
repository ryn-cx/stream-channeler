# TODO: Validate
"""Source service functions."""

from plugins.utils.abstract_plugin import AbstractPlugin
from plugins.utils.manage_plugins import sorted_plugins

OTHER_SOURCE_KEY = "Other"


def _owns_source(plugin: type[AbstractPlugin]) -> bool:
    """Return whether the plugin creates a `Source` of its own."""
    from plugins.utils.base_plugin.plugin import BasePlugin  # noqa: PLC0415

    return (
        issubclass(plugin, BasePlugin)
        and plugin.initialize_source is BasePlugin.initialize_source
    )


def official_source_keys() -> list[str]:
    """Return the keys of every plugin that can own episodes.

    Lookup-only plugins (e.g. TMDB) never own a `Source`, so URL import support is
    required. JustWatch does import URLs, but only through other plugins, so
    plugins without a `Source` of their own are excluded as well.
    """
    return [
        plugin.plugin_key()
        for plugin in sorted_plugins()
        if plugin.implements("import_url") and _owns_source(plugin)
    ]


def source_favicons() -> dict[str, str | None]:
    """Return every plugin's favicon URL, keyed by its source key."""
    return {plugin.plugin_key(): plugin.FAVICON_URL for plugin in sorted_plugins()}


def source_names() -> dict[str, str]:
    """Return every plugin's display name, keyed by its source key."""
    return {plugin.plugin_key(): plugin.plugin_name() for plugin in sorted_plugins()}


def source_names() -> dict[str, str]:
    """Return every plugin's display name, keyed by its source key."""
    return {plugin.plugin_key(): plugin.plugin_name() for plugin in sorted_plugins()}
