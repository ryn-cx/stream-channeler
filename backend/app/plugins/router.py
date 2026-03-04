from fastapi import APIRouter
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import create_record, delete_record, list_records, update_record
from app.models import Message
from app.plugins.dependencies import UserPlugin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginInput,
    PluginOutput,
    PluginPatchInput,
    PluginPostInput,
    PluginsListOutput,
)
from app.sources.models import Source
from app.sources.schemas import (
    SourceInput,
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
    statement = select(Plugin).where(Plugin.user_id == current_user.id)
    plugins = session.exec(statement).all()
    data = [PluginOutput.model_validate(plugin) for plugin in plugins]
    return PluginsListOutput(data=data, count=len(data))


# FAST003 - Parameter is used by UserPlugin.
@router.get("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003
def get_user_plugin(plugin: UserPlugin) -> Plugin:
    """Get a plugin owned by the current user by its id."""
    return plugin


# FAST003 - Parameter is used by UserPlugin.
@router.get("/{plugin_id}/sources")  # noqa: FAST003
def get_user_plugin_sources(
    session: SessionDep,
    plugin: UserPlugin,
) -> SourcesListOutput:
    """List all sources for a plugin owned by the current user."""
    return list_records(
        session=session,
        parent=plugin,
        child_model=Source,
        parent_key="plugin_id",
        list_output=SourcesListOutput,
    )


# FAST003 - Parameter is used by UserPlugin.
@router.post("/{plugin_id}/sources", response_model=SourceOutput)  # noqa: FAST003
def create_user_source(
    session: SessionDep,
    plugin: UserPlugin,
    source_input: SourcePostInput,
) -> Source:
    """Create a source for a plugin."""
    return create_record(
        session=session,
        parent=plugin,
        post_input=source_input,
        input_schema=SourceInput,
        existing=Source.get(session, plugin, source_input.key),
    )


@router.post("", response_model=PluginOutput)
def create_user_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_input: PluginPostInput,
) -> Plugin:
    """Create a plugin owned by the current user."""
    return create_record(
        session=session,
        parent=current_user,
        post_input=plugin_input,
        input_schema=PluginInput,
        existing=Plugin.get(session, plugin_input.key, user_id=current_user.id),
    )


# FAST003 - Parameter is used by UserPlugin.
@router.patch("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003
def update_user_plugin(
    session: SessionDep,
    plugin: UserPlugin,
    plugin_input: PluginPatchInput,
) -> Plugin:
    """Update a plugin owned by the current user."""
    return update_record(
        session=session,
        entry=plugin,
        body=plugin_input,
    )


# FAST003 - Parameter is used by UserPlugin.
@router.delete("/{plugin_id}")  # noqa: FAST003
def delete_user_plugin(session: SessionDep, plugin: UserPlugin) -> Message:
    """Delete a plugin owned by the current user."""
    return delete_record(
        session=session,
        entry=plugin,
        model_name="Plugin",
    )
