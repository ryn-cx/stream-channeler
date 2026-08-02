# TODO: Validate

from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.plugins import service
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
    TMDBMediaInfo,
    TMDBMediaType,
    TMDBSearchResultItem,
)
from app.schemas import Message
from app.users.models import User
from plugins.utils.abstract_plugin import PluginSearchResults
from plugins.utils.manage_plugins import sorted_plugins_for_user

plugins_router = APIRouter(prefix="/plugins", tags=["plugins"])

PLUGIN_EXTRA_COLUMNS: dict[str, Any] = {"username": User.username}


# A `Plugin`'s parent is the `User` that owns it rather than another media record, so
# the create route resolves the requester instead of a record they can edit.
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


@plugins_router.patch("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by EditablePlugin.
def update_plugin(
    session: SessionDep,
    plugin: EditablePlugin,
    plugin_input: PluginUpdate,
) -> Plugin:
    """Update and return a `Plugin` if it's editable by the `User`."""
    return plugin_input.update(session, plugin)


@plugins_router.delete("/{plugin_id}")  # noqa: FAST003 - Used by EditablePlugin.
def delete_plugin(session: SessionDep, plugin: EditablePlugin) -> Message:
    """Delete a `Plugin` if it's editable by the `User`."""
    return delete_record(session, plugin)


@plugins_router.get("/import-watch-history-information")
def import_watch_history_information(
    current_user: CurrentUser,
) -> list[PluginImportWatchHistoryInformation]:
    """Return information about all plugins that support importing watch history."""
    return [
        PluginImportWatchHistoryInformation(
            plugin_key=plugin_cls.plugin_key(),
            file_extension=plugin_cls.import_watch_history_file_extension,
            instructions=plugin_cls.import_watch_history_instructions(),
        )
        for plugin_cls in sorted_plugins_for_user(
            is_superuser=current_user.is_superuser,
        )
        if plugin_cls.implements("import_watch_history")
    ]


@plugins_router.get("/import-url-information")
def import_url_information(
    current_user: CurrentUser,
) -> list[PluginImportURLInformation]:
    """Return information about all plugins that support importing URLs."""
    return [
        PluginImportURLInformation(
            name=plugin_cls.plugin_key(),
            instructions=plugin_cls.import_url_instructions(),
            favicon_url=plugin_cls.FAVICON_URL,
        )
        for plugin_cls in sorted_plugins_for_user(
            is_superuser=current_user.is_superuser,
        )
        if plugin_cls.implements("import_url")
    ]


@plugins_router.get("/match-url")
def match_url(
    url: str,
    current_user: CurrentUser,
) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    for plugin_cls in sorted_plugins_for_user(is_superuser=current_user.is_superuser):
        if plugin_cls.implements("import_url") and plugin_cls.is_valid_url_format(url):
            return PluginURLMatch(matched=True, plugin_key=plugin_cls.plugin_key())
    return PluginURLMatch(matched=False)


@plugins_router.get("/search-information")
def search_information(
    current_user: CurrentUser,
) -> list[PluginSearchInformation]:
    available_plugins = sorted_plugins_for_user(
        is_superuser=current_user.is_superuser,
    )
    in_app_search = [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
            favicon_url=plugin_cls.FAVICON_URL,
        )
        for plugin_cls in available_plugins
        if plugin_cls.implements("search")
    ]
    manual_search = [
        PluginSearchInformation(
            plugin_key=plugin_cls.plugin_key(),
            name=plugin_cls.plugin_key(),
            manual_search_only=True,
            favicon_url=plugin_cls.FAVICON_URL,
        )
        for plugin_cls in available_plugins
        if not plugin_cls.implements("search")
        and plugin_cls.implements("search_url")
    ]
    return in_app_search + manual_search


@plugins_router.get("/search-url")
def search_url(
    plugin_key: str,
    query: str,
    current_user: CurrentUser,
) -> PluginSearchUrl:
    """Return a plugin website's own search-page URL for `query`."""
    for plugin_cls in sorted_plugins_for_user(is_superuser=current_user.is_superuser):
        if plugin_cls.plugin_key() == plugin_key:
            return PluginSearchUrl(url=plugin_cls.search_url(query))
    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


@plugins_router.get("/search")
def search_plugin(
    plugin_key: str,
    query: str,
    session: SessionDep,
    current_user: CurrentUser,
) -> PluginSearchResults:
    """Search for shows/movies on a plugin's platform."""
    for plugin_cls in sorted_plugins_for_user(is_superuser=current_user.is_superuser):
        if plugin_cls.plugin_key() == plugin_key:
            if not plugin_cls.implements("search"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' does not support search.",
                )
            return plugin_cls(session).search(query)

    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


@plugins_router.get("/tmdb/search")
def tmdb_search(
    query: str,
    session: SessionDep,
    _current_user: CurrentUser,
) -> list[TMDBSearchResultItem]:
    """Search movies and TV across all of TMDB, ranked by title similarity."""
    return service.tmdb_search(session, query)


@plugins_router.get("/tmdb/media-info")
def tmdb_media_info(
    media_type: TMDBMediaType,
    tmdb_id: int,
    session: SessionDep,
    _current_user: CurrentUser,
) -> TMDBMediaInfo | None:
    """Return rich detail and US watch providers for one TMDB movie or TV show."""
    return service.tmdb_media_info(session, media_type, tmdb_id)


# Registered after the literal paths above so that they are matched first.
@plugins_router.get("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by ReadablePlugin.
def get_plugin(plugin: ReadablePlugin) -> Plugin:
    """Get a `Plugin` if it's readable by the `User`."""
    return plugin


router = APIRouter()
router.include_router(plugins_router)
