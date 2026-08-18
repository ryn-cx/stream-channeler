# TODO: Validate
import importlib
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
def try_to_import_plugin(plugin_import_path: str) -> None:
    try:
        importlib.import_module(plugin_import_path)
    except ImportError:
        msg = f"Failed to import plugin: {plugin_import_path}."
        logger.exception(msg)


_plugins_loaded = False


# TODO: Validate
def import_plugins() -> None:
    """Import and register all plugins in the plugins folder.

    Safe to call multiple times — only performs the import once.
    """
    global _plugins_loaded  # noqa: PLW0603
    if _plugins_loaded:
        return
    _plugins_loaded = True

    plugins_dir = Path(__file__).parent.parent
    # plugins can either be a single file or a folder with multiple files so both
    # formats have to be supported.
    for plugin_path in plugins_dir.glob("*"):
        # Assume any file starting with an underscore is not a plugin to avoid things
        # files like __pycache__ and __init__.py, will also allow users to easily
        # disable a plugin by renaming it to start with an underscore.
        if plugin_path.name.startswith("_"):
            continue

        # Skip the utils folder because it should contain no plugins.
        if plugin_path.name == "utils":
            continue

        if plugin_path.is_dir():
            try_to_import_plugin(f"plugins.{plugin_path.name}")
        elif plugin_path.suffix == ".py":
            try_to_import_plugin(f"plugins.{plugin_path.stem}")


plugins: set[type[AbstractPlugin]] = set()
"""Track all of the plugins that have been registered."""


# TODO: Validate
def register_plugins(plugin: type[AbstractPlugin]) -> None:
    """Register all plugins in the plugins folder."""
    plugins.add(plugin)


# TODO: Validate
def sorted_plugins() -> list[type[AbstractPlugin]]:
    """Return the registered plugins sorted by their plugin_key."""
    import_plugins()
    return sorted(plugins, key=lambda plugin: plugin.plugin_key())


# TODO: Validate
def plugin_for_url(
    url: str,
    exclude: type[AbstractPlugin] | None = None,
) -> type[AbstractPlugin] | None:
    """Return the plugin that imports `url` itself, if there is one."""
    for plugin_class in sorted_plugins():
        if (
            plugin_class is not exclude
            and plugin_class.implements("import_url")
            and plugin_class.is_valid_url_format(url)
        ):
            return plugin_class
    return None
