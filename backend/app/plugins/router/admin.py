# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.media.service import delete_record
from app.plugins.dependencies import ExistingPlugin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginListOutput,
    PluginOutput,
    PluginsPublic,
    PluginUpdate,
)
from app.schemas import Message, ReadOptions
from app.service import list_response

plugins_router = APIRouter(
    prefix="/plugins",
    tags=["plugins"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@plugins_router.post(
    "",
    response_model=PluginOutput,
)
def create_plugin(
    session: SessionDep,
    plugin_input: PluginCreate,
) -> Plugin:
    """Create a `Plugin`."""
    return plugin_input.create(session)


# TODO: Validate
@plugins_router.get("")
def get_plugins(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> PluginsPublic:
    """Get `Plugin`s."""
    return list_response(
        session=session,
        base=Plugin.select_with_plugin(),
        response_model=PluginsPublic,
        schema=PluginListOutput,
        params=read_options,
        current_user=current_user,
    )


# TODO: Validate
@plugins_router.patch(
    "/{plugin_id}",
    response_model=PluginOutput,
)
def update_plugin(
    session: SessionDep,
    plugin: ExistingPlugin,
    plugin_input: PluginUpdate,
) -> Plugin:
    return plugin_input.update(session, plugin)


# TODO: Validate
@plugins_router.delete(
    "/{plugin_id}",
)
def delete_plugin(session: SessionDep, plugin: ExistingPlugin) -> Message:
    return delete_record(session, plugin)


# TODO: Validate
@plugins_router.get(
    "/{plugin_id}",
    response_model=PluginOutput,
)
def get_plugin(plugin: ExistingPlugin) -> Plugin:
    return plugin


router = APIRouter()
router.include_router(plugins_router)
