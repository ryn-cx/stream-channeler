# TODO: Validate

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.media.schemas import MediaReadOptions
from app.media.service import delete_record, media_owner_list_response
from app.plugins.dependencies import EditablePlugin, ReadablePlugin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginOutput,
    PluginSearchInformation,
    PluginsPublic,
    PluginUpdate,
    PluginURLMatch,
)
from app.schemas import Message
from plugins.utils.abstract_plugin import PluginSearchResults
from plugins.utils.manage_plugins import sorted_plugins

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])


@plugins_router.post("", response_model=PluginOutput)
def create_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_input: PluginCreate,
) -> Plugin:
    """Create a `Plugin` owned by the `User`."""
    return plugin_input.create(session, Plugin, current_user)


@plugins_router.get("")
def get_plugins(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> PluginsPublic:
    """Get all of the `Plugin`s readable by the `User`."""
    return media_owner_list_response(
        session=session,
        base=select(Plugin),
        response_model=PluginsPublic,
        schema=PluginOutput,
        read_options=read_options,
        current_user=current_user,
    )


@plugins_router.patch("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by EditablePlugin
def update_plugin(
    session: SessionDep,
    plugin: EditablePlugin,
    plugin_input: PluginUpdate,
) -> Plugin:
    """Update and return a `Plugin` if it's editable by the `User`."""
    return plugin_input.update(session, plugin)


@plugins_router.delete("/{plugin_id}")  # noqa: FAST003 - Used by EditablePlugin
def delete_plugin(session: SessionDep, plugin: EditablePlugin) -> Message:
    """Delete a `Plugin` if it's editable by the `User`."""
    return delete_record(session, plugin)


@plugins_router.get("/import-watch-history-information")
def import_watch_history_information(
    _current_user: CurrentUser,
) -> list[PluginImportWatchHistoryInformation]:
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


@plugins_router.get("/import-url-information")
def import_url_information(
    _current_user: CurrentUser,
) -> list[PluginImportURLInformation]:
    """Return information about all plugins that support importing URLs."""
    return [
        PluginImportURLInformation(
            name=plugin_cls.plugin_key(),
            instructions=plugin_cls.import_url_instructions(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("import_url")
    ]


@plugins_router.get("/match-url")
def match_url(
    url: str,
    _current_user: CurrentUser,
) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.implements("import_url") and plugin_cls.is_valid_url_format(url):
            return PluginURLMatch(matched=True, plugin_key=plugin_cls.plugin_key())
    return PluginURLMatch(matched=False)


@plugins_router.get("/search-information")
def search_information(
    _current_user: CurrentUser,
) -> list[PluginSearchInformation]:
    """Return information about all plugins that support searching."""
    return [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("search")
    ]


@plugins_router.get("/search")
def search_plugin(
    plugin_key: str,
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
) -> PluginSearchResults:
    """Search for shows/movies on a plugin's platform."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.implements("search"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' does not support search.",
                )
            return plugin_cls(session).search(query)

    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


@plugins_router.get("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by ReadablePlugin
def get_plugin(plugin: ReadablePlugin) -> Plugin:
    """Get a `Plugin` if it's readable by the `User`."""
    return plugin


router = APIRouter()
router.include_router(plugins_router)
