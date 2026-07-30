# TODO: Validate
"""Source service functions."""

from plugins.utils.manage_plugins import sorted_plugins

OTHER_SOURCE_KEY = "Other"


def official_source_keys() -> list[str]:
    """Return the keys of every plugin that can own episodes.

    Lookup-only plugins (e.g. TMDB) never own a `Source`, so they are excluded by
    requiring URL import support.
    """
    return [
        plugin.plugin_key()
        for plugin in sorted_plugins()
        if plugin.implements("import_url")
    ]
