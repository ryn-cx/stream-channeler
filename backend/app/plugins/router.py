from fastapi import APIRouter

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import (
    create_child,
    delete_record,
    list_children,
    raise_if_exists,
    update_record,
)
from app.models import Message
from app.plugins.dependencies import ReadablePlugin, UserPlugin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
    PluginsListOutput,
)
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePostInput,
    SourcesListOutput,
)

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("")
def get_user_plugins(
    session: SessionDep,
    current_user: CurrentUser,
) -> PluginsListOutput:
    """List all plugins owned by the current user."""
    return list_children(
        session,
        Plugin,
        "user_id",
        current_user.id,
        PluginOutput,
        PluginsListOutput,
    )


# FAST003 - Parameter is used by ReadablePlugin.
@router.get("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003
def get_user_plugin(plugin: ReadablePlugin) -> Plugin:
    """Get a plugin by its id if it is public or owned by the current user."""
    return plugin


# FAST003 - Parameter is used by ReadablePlugin.
@router.get("/{plugin_id}/sources")  # noqa: FAST003
def get_user_plugin_sources(
    session: SessionDep,
    plugin: ReadablePlugin,
) -> SourcesListOutput:
    """List all sources for a plugin if it is public or owned by the current user."""
    return list_children(
        session,
        Source,
        "plugin_id",
        plugin.id,
        SourceOutput,
        SourcesListOutput,
    )


# FAST003 - Parameter is used by UserPlugin.
@router.post("/{plugin_id}/sources", response_model=SourceOutput)  # noqa: FAST003
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
    raise_if_exists(Plugin.get(session, plugin_input.key, user_id=current_user.id))
    plugin = Plugin.model_validate(plugin_input, update={"user_id": current_user.id})
    session.add(plugin)
    session.commit()
    return plugin


# FAST003 - Parameter is used by UserPlugin.
@router.patch("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003
def update_user_plugin(
    session: SessionDep,
    plugin: UserPlugin,
    plugin_input: PluginPatchInput,
) -> Plugin:
    """Update a plugin owned by the current user."""
    return update_record(session, plugin, plugin_input)


# FAST003 - Parameter is used by UserPlugin.
@router.delete("/{plugin_id}")  # noqa: FAST003
def delete_user_plugin(session: SessionDep, plugin: UserPlugin) -> Message:
    """Delete a plugin owned by the current user."""
    return delete_record(session, plugin, "Plugin")
