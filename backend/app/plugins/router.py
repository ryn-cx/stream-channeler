# TODO: Validate

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.plugins.dependencies import EditablePlugin, ReadablePlugin
from app.plugins.models import Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginListOutput,
    PluginOutput,
    PluginSearchInformation,
    PluginSearchUrl,
    PluginsPublic,
    PluginUpdate,
    PluginURLMatch,
)
from app.schemas import Message
from app.users.models import User
from plugins.utils.abstract_plugin import PluginMediaInfo, PluginSearchResults
from plugins.utils.manage_plugins import sorted_plugins

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])

PLUGIN_EXTRA_COLUMNS: dict[str, Any] = {"username": User.username}


# A `Plugin`'s parent is the `User` that owns it rather than another media record, so
# the create route resolves the requester instead of a record they can edit.
# TODO: Validate
@plugins_router.post(
    "",
    response_model=PluginOutput,
    dependencies=[Depends(get_current_active_superuser)],
)
def create_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_input: PluginCreate,
) -> Plugin:
    """Create a `Plugin` owned by the `User`."""
    return plugin_input.create(session, Plugin, current_user)


# TODO: Validate
@plugins_router.get("", dependencies=[Depends(get_current_active_superuser)])
def get_plugins(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> PluginsPublic:
    """Get `Plugin`s."""
    return media_scoped_list_response(
        session=session,
        base=Plugin.select_with_user_eager(),
        response_model=PluginsPublic,
        schema=PluginListOutput,
        read_options=read_options,
        current_user=current_user,
        extra_columns=PLUGIN_EXTRA_COLUMNS,
    )


# TODO: Validate
@plugins_router.patch(
    "/{plugin_id}",
    response_model=PluginOutput,
    dependencies=[Depends(get_current_active_superuser)],
)
def update_plugin(
    session: SessionDep,
    plugin: EditablePlugin,
    plugin_input: PluginUpdate,
) -> Plugin:
    """Update and return a `Plugin` if it's editable by the `User`."""
    return plugin_input.update(session, plugin)


# TODO: Validate
@plugins_router.delete(
    "/{plugin_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_plugin(session: SessionDep, plugin: EditablePlugin) -> Message:
    """Delete a `Plugin` if it's editable by the `User`."""
    return delete_record(session, plugin)


# TODO: Validate
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


# TODO: Validate
@plugins_router.get("/import-url-information")
def import_url_information(
    _current_user: CurrentUser,
) -> list[PluginImportURLInformation]:
    """Return information about the plugins offered as ways to add by URL.

    A plugin that imports URLs but is only reached through another one is left
    out. `match-url` still resolves its URLs, so one a `User` pastes anyway is
    imported rather than rejected.
    """
    return [
        PluginImportURLInformation(
            name=plugin_cls.plugin_key(),
            instructions=plugin_cls.import_url_instructions(),
            favicon_url=plugin_cls.FAVICON_URL,
        )
        for plugin_cls in sorted_plugins()
        if plugin_cls.implements("import_url")
    ]


# TODO: Validate
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


# TODO: Validate
@plugins_router.get("/search-information")
def search_information(
    _current_user: CurrentUser,
) -> list[PluginSearchInformation]:
    searchable = [
        plugin_cls for plugin_cls in sorted_plugins() if plugin_cls.USER_SEARCHABLE
    ]
    in_app_search = [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
            favicon_url=plugin_cls.FAVICON_URL,
        )
        for plugin_cls in searchable
        if plugin_cls.implements("search")
    ]
    manual_search = [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
            manual_search_only=True,
            favicon_url=plugin_cls.FAVICON_URL,
        )
        for plugin_cls in searchable
        if not plugin_cls.implements("search") and plugin_cls.implements("search_url")
    ]
    return in_app_search + manual_search


# TODO: Validate
@plugins_router.get("/search-url")
def search_url(
    plugin_key: str,
    query: str,
    _current_user: CurrentUser,
) -> PluginSearchUrl:
    """Return a plugin website's own search-page URL for `query`."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.USER_SEARCHABLE:
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' cannot be searched.",
                )
            return PluginSearchUrl(url=plugin_cls.search_url(query))
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


# TODO: Validate
@plugins_router.get("/search")
def search_plugin(
    plugin_key: str,
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
    cursor: str | None = None,
) -> PluginSearchResults:
    """Search for shows/movies on a plugin's platform.

    `cursor` is the `next_cursor` of an earlier page; omit it for the first one.
    """
    for plugin_cls in sorted_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.USER_SEARCHABLE:
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' cannot be searched.",
                )
            if not plugin_cls.implements("search"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' does not support search.",
                )
            return plugin_cls(session).search(query, cursor)

    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


# TODO: Validate
@plugins_router.get("/media-info")
def media_info(
    plugin_key: str,
    media_identifier: str,
    session: SessionDep,
    _current_user: CurrentUser,
) -> PluginMediaInfo | None:
    """Return everything a plugin knows about one of its own search results.

    Answered by the same plugin the result came from, under the identifier that
    plugin issued, so a title's detail is the source's own rather than whatever
    a search of some other service turned up.
    """
    for plugin_cls in sorted_plugins():
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.implements("media_info"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' does not support media info.",
                )
            return plugin_cls(session).media_info(media_identifier)

    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


# Registered after the literal paths above so that they are matched first.
# TODO: Validate
@plugins_router.get(
    "/{plugin_id}",
    response_model=PluginOutput,
    dependencies=[Depends(get_current_active_superuser)],
)
def get_plugin(plugin: ReadablePlugin) -> Plugin:
    """Get a `Plugin` if it's readable by the `User`."""
    return plugin


router = APIRouter()
router.include_router(plugins_router)
