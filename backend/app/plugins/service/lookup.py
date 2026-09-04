# TODO: Validate
from fastapi import HTTPException

from plugins.utils.abstract_plugin import (
    AbstractPlugin,
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
        if plugin_cls.plugin_name() == plugin_key:
            if not plugin_cls.implements(capability):
                raise HTTPException(status_code=422, detail=refusal)
            return plugin_cls
    raise HTTPException(
        status_code=404,
        detail=f"Plugin {plugin_key!r} not found.",
    )
