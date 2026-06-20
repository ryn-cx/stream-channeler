# TODO: Validate
from collections.abc import Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.files.schemas import FileCreate, FileListPublic, FilePublic
from app.media.service import (
    delete_record,
)
from app.plugins.dependencies import OwnedPlugin, ReadablePlugin
from app.plugins.models import File, Plugin
from app.plugins.schemas import (
    PluginCreate,
    PluginImportURLInformation,
    PluginImportWatchHistoryInformation,
    PluginOutput,
    PluginSearchInformation,
    PluginUpdate,
    PluginURLMatch,
)
from app.schemas import Message
from app.sources.models import Source
from app.sources.schemas import SourceCreate, SourcePublic
from app.users.service import get_or_create_plugin_user
from plugins.utils.abstract_plugin import PluginSearchResults
from plugins.utils.manage_plugins import sorted_plugins

router = APIRouter(prefix="/plugins", tags=["plugins"])


@router.get("/import-watch-history-information")
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


@router.get("/import-url-information")
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


@router.get("/match-url")
def match_url(
    url: str,
    _current_user: CurrentUser,
) -> PluginURLMatch:
    """Return whether any plugin can import `url`."""
    for plugin_cls in sorted_plugins():
        if plugin_cls.implements("import_url") and plugin_cls.is_valid_url_format(url):
            return PluginURLMatch(matched=True, plugin_key=plugin_cls.plugin_key())
    return PluginURLMatch(matched=False)


@router.get("/search-information")
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
            if not plugin_cls.implements("search"):
                raise HTTPException(
                    status_code=422,
                    detail=f"Plugin '{plugin_key}' does not support search.",
                )
            return plugin_cls(session).search(query)

    raise HTTPException(status_code=404, detail=f"Plugin '{plugin_key}' not found.")


@router.get("", response_model=list[PluginOutput])
def get_plugins(session: SessionDep, current_user: CurrentUser) -> list[Plugin]:
    """Get all `Plugin`s owned by the current `User`.

    Superusers also see all `Plugin`s owned by the plugin user (official media),
    listed after the user's own plugins.
    """
    if current_user.is_superuser:
        plugin_user = get_or_create_plugin_user(session=session)
        return current_user.plugins + plugin_user.plugins

    return current_user.plugins


@router.post("", response_model=PluginOutput)
def create_plugin(
    session: SessionDep,
    current_user: CurrentUser,
    plugin_input: PluginCreate,
) -> Plugin:
    """Create a `Plugin` owned by the current `User`."""
    return plugin_input.create(session, Plugin, current_user)


@router.get("/{plugin_id}/sources", response_model=list[SourcePublic])  # noqa: FAST003 - Used by ReadablePlugin
def get_plugin_sources(plugin: ReadablePlugin) -> list[Source]:
    """List all `Source`s for a `Plugin` if it is public or owned by the current `User`."""
    return plugin.sources


@router.post("/{plugin_id}/sources", response_model=SourcePublic)  # noqa: FAST003 - Used by OwnedPlugin
def create_source(
    session: SessionDep,
    plugin: OwnedPlugin,
    source_input: SourceCreate,
) -> Source:
    """Create a `Source` if the `Plugin` is owned by the current `User`."""
    return source_input.create(session, Source, plugin)


@router.get(
    "/{plugin_id}/files",  # noqa: FAST003 - Used by ReadablePlugin
    response_model=list[FileListPublic],
    dependencies=[Depends(get_current_active_superuser)],
)
def get_plugin_files(
    plugin: ReadablePlugin,
    session: SessionDep,
    content: str | None = None,
) -> Sequence[File]:
    """List all `File`s for a `Plugin` if it is public or owned by the current `User`."""
    statement = select(File).where(col(File.plugin_id) == plugin.id)
    if content:
        statement = statement.where(col(File.content).ilike(f"%{content}%"))
    return session.exec(statement).all()


@router.post(
    "/{plugin_id}/files",  # noqa: FAST003 - Used by OwnedPlugin
    response_model=FilePublic,
    dependencies=[Depends(get_current_active_superuser)],
)
def create_file(
    session: SessionDep,
    plugin: OwnedPlugin,
    file_input: FileCreate,
) -> File:
    """Create a `File` if the `Plugin` is owned by the current `User`."""
    return file_input.create(session, File, plugin)


@router.patch("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by OwnedPlugin
def update_plugin(
    session: SessionDep,
    plugin: OwnedPlugin,
    plugin_input: PluginUpdate,
) -> Plugin:
    """Update and return a `Plugin` if it's owned by the current `User`."""
    return plugin_input.update(session, plugin)


@router.delete("/{plugin_id}")  # noqa: FAST003 - Used by OwnedPlugin
def delete_plugin(session: SessionDep, plugin: OwnedPlugin) -> Message:
    """Delete a `Plugin` if it's owned by the current `User`."""
    return delete_record(session, plugin)


@router.get("/{plugin_id}", response_model=PluginOutput)  # noqa: FAST003 - Used by ReadablePlugin
def get_plugin(plugin: ReadablePlugin) -> Plugin:
    """Get a `Plugin` if it's readable by the current `User`."""
    return plugin
