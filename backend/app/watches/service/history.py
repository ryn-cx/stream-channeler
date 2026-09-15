# TODO: Validate
from typing import TYPE_CHECKING

from fastapi import HTTPException, UploadFile
from sqlmodel import Session

from app.plugins.models import Plugin
from app.users.models import User
from app.watches.schemas import (
    WatchExportEntry,
    WatchImportInput,
    WatchImportResults,
)
from plugins.StreamChanneler import StreamChanneler
from plugins.utils.manage_plugins import import_plugins, plugins

if TYPE_CHECKING:
    from plugins.utils.abstract_plugin import AbstractPlugin


# TODO: Validate
def get_plugins_with_import_watch_history(
    session: Session,
) -> list[type[AbstractPlugin]]:
    """Return all plugin classes that support watch import."""
    import_plugins()
    return [
        plugin_cls
        for plugin_cls in plugins
        if plugin_cls.implements("import_watch_history")
        and Plugin.get(session, plugin_cls.plugin_name())
    ]


# TODO: Validate
def get_installed_plugin(plugin_key: str) -> type[AbstractPlugin] | None:
    """Find an importable plugin class by its plugin_key."""
    import_plugins()
    for plugin_cls in plugins:
        if plugin_cls.plugin_name() == plugin_key:
            return plugin_cls
    return None


# TODO: Validate
def import_watch_history_file(
    session: Session,
    current_user: User,
    file: UploadFile,
    params: WatchImportInput,
) -> WatchImportResults:
    """Read a watch history a plugin wrote out and record what it says."""
    plugin = get_installed_plugin(params.plugin_key)
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin {params.plugin_key!r} not found.",
        )
    if not plugin.implements("import_watch_history"):
        raise HTTPException(
            status_code=422,
            detail=f"Plugin {params.plugin_key!r} does not support watch history import.",
        )

    result = plugin(session=session).import_watch_history(
        content=file.file.read().decode("utf-8"),
        user=current_user,
        new_only=params.new_only,
        verified=params.verified,
    )
    session.commit()
    return result


# TODO: Validate
def export_watch_history_entries(
    session: Session,
    current_user: User,
) -> list[WatchExportEntry]:
    """Write out the `User`'s watches as a Stream Channeler watch history."""
    return StreamChanneler(session=session).export_watch_history(current_user)
