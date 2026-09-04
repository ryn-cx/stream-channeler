# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.plugins.dependencies import ExistingPlugin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginListOutput,
    PluginOutput,
    PluginsPublic,
)
from app.schemas import ReadOptions
from app.service.responses import list_response

plugins_router = APIRouter(
    prefix="/plugins",
    tags=["plugins"],
    dependencies=[Depends(get_current_active_superuser)],
)


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
@plugins_router.get(
    "/{plugin_id}",
    response_model=PluginOutput,
)
def get_plugin(plugin: ExistingPlugin) -> Plugin:
    return plugin


router = APIRouter()
router.include_router(plugins_router)
