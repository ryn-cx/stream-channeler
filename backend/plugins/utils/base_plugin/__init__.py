# TODO: Validate
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from plugins.utils.base_plugin.plugin import BasePlugin
    from plugins.utils.base_plugin.watch_history import (
        ParsedWatchEntry,
        WatchHistoryMixin,
    )

__all__ = [
    "BasePlugin",
    "ParsedWatchEntry",
    "WatchHistoryMixin",
]

_MODULES = {
    "BasePlugin": "plugins.utils.base_plugin.plugin",
    "ParsedWatchEntry": "plugins.utils.base_plugin.watch_history",
    "WatchHistoryMixin": "plugins.utils.base_plugin.watch_history",
}


# TODO: Validate
def __getattr__(name: str) -> Any:  # noqa: ANN401 - One of several exported classes.
    if (module_name := _MODULES.get(name)) is None:
        msg = f"module {__name__!r} has no attribute {name!r}"
        raise AttributeError(msg)

    import importlib  # noqa: PLC0415

    return getattr(importlib.import_module(module_name), name)
