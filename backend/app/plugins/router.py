# TODO: Validate
from fastapi import APIRouter, HTTPException, status

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import (
    create_child,
    delete_record,
    list_children,
    raise_if_exists,
    update_record,
)
from app.plugins.dependencies import ReadablePlugin, UserPlugin
from app.plugins.models import Plugin
from app.plugins.plugins.utils.abstract_plugin import PluginSearchResults
from app.plugins.plugins.utils.manage_plugins import sorted_plugins
from app.plugins.schemas import (
    PluginImportURLInfo,
    PluginImportWatchHistoryInfo,
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
    PluginSearchInfo,
)
from app.schemas import Message
from app.sources.models import Source
from app.sources.schemas import SourceOutput, SourcePostInput

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("", response_model=list[PluginOutput])
def get_user_plugins(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[Plugin]:
    """List all plugins owned by the current user."""
    return list_children(session, Plugin, "user_id", current_user.id)


@router.get("/supports-import-watch-history")
def list_plugins_that_support_import_watch_history(
    _current_user: CurrentUser,
) -> list[PluginImportWatchHistoryInfo]:
    """List all plugins that support importing watch history."""
    return [
        PluginImportWatchHistoryInfo(
            plugin_key=plugin_cls.plugin_key(),
            file_extension=plugin_cls.import_watch_history_file_extension,
            instructions=plugin_cls.import_watch_history_instructions(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.supports_import_watch_history
    ]


@router.get("/supports-import-url")
def list_plugins_that_support_import_url(
    _current_user: CurrentUser,
) -> list[PluginImportURLInfo]:
    """List all plugins that support URL importing."""
    return [
        PluginImportURLInfo(
            name=plugin_cls.plugin_key(),
            instructions=plugin_cls.import_url_instructions(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.supports_import_url
    ]


@router.get("/supports-search")
def list_plugins_that_support_search(
    _current_user: CurrentUser,
) -> list[PluginSearchInfo]:
    """List all plugins that support searching."""
    return [
        PluginSearchInfo(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.supports_search
    ]


@router.get("/search")
def search_plugin(
    plugin_key: str,
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
) -> PluginSearchResults:
    """Search for shows/movies on a plugin's platform."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.supports_search:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=f"Plugin '{plugin_key}' does not support search.",
                )
            return plugin_cls(session).search(query)

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Plugin '{plugin_key}' not found.",
    )


@router.get("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by ReadablePlugin
def get_user_plugin(plugin: ReadablePlugin) -> Plugin:
    """Get a plugin by its id if it is public or owned by the current user."""
    return plugin


@router.get("/{plugin_id}/sources", response_model=list[SourceOutput])  # noqa: FAST003 - Used by ReadablePlugin
def get_user_plugin_sources(
    session: SessionDep,
    plugin: ReadablePlugin,
) -> list[Source]:
    """List all sources for a plugin if it is public or owned by the current user."""
    return list_children(session, Source, "plugin_id", plugin.id)


@router.post("/{plugin_id}/sources", response_model=SourceOutput)  # noqa: FAST003 - Used by UserPlugin
def create_user_source(
    session: SessionDep,
    plugin: UserPlugin,
    source_input: SourcePostInput,
) -> Source:
    """Create a source for a plugin."""
    return create_child(session, Source, plugin, source_input, "plugin_id")


@router.post("", response_model=PluginOutput)
def create_user_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_input: PluginPostInput,
) -> Plugin:
    """Create a plugin owned by the current user."""
    raise_if_exists(Plugin.get(session, plugin_input.key, current_user))
    plugin = Plugin.model_validate(plugin_input, update={"user_id": current_user.id})
    session.add(plugin)
    session.commit()
    return plugin


@router.patch("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by UserPlugin
def update_user_plugin(
    session: SessionDep,
    plugin: UserPlugin,
    plugin_input: PluginPatchInput,
) -> Plugin:
    """Update a plugin owned by the current user."""
    return update_record(session, plugin, plugin_input)


@router.delete("/{plugin_id}")  # noqa: FAST003 - Used by UserPlugin
def delete_user_plugin(session: SessionDep, plugin: UserPlugin) -> Message:
    """Delete a plugin owned by the current user."""
    return delete_record(session, plugin)
