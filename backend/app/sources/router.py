# TODO: Validate
"""Source router."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.plugins.dependencies import EditablePlugin, ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.sources.dependencies import EditableSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourceListPublic,
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
)
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_sources_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["sources"])
sources_router = APIRouter(prefix="/sources", tags=["sources"])

SOURCE_EXTRA_COLUMNS: dict[str, Any] = {
    "username": User.username,
    "plugin_name": Plugin.name,
}


# TODO: Validate
@plugin_sources_router.post("/sources", response_model=SourcePublic)
def create_source(
    session: SessionDep,
    plugin: EditablePlugin,
    source_input: SourceCreate,
) -> Source:
    """Create a `Source` if the `Plugin` is editable by the `User`."""
    return source_input.create(session, Source, plugin)


# TODO: Validate
@sources_router.get("")
def get_sources(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SourcesPublic:
    """Get `Source`s."""
    return media_scoped_list_response(
        session=session,
        base=Source.select_with_user_eager(),
        response_model=SourcesPublic,
        schema=SourceListPublic,
        read_options=read_options,
        current_user=current_user,
        extra_columns=SOURCE_EXTRA_COLUMNS,
    )


# TODO: Validate
@plugin_sources_router.get("/sources")
def get_plugin_sources(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SourcesPublic:
    """Get all of the `Source`s for a `Plugin` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Source.select_with_user_eager().where(Source.plugin_id == plugin.id),
        response_model=SourcesPublic,
        schema=SourceListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SOURCE_EXTRA_COLUMNS,
    )


# TODO: Validate
@sources_router.get("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by ReadableSource.
def get_source(source: ReadableSource) -> Source:
    """Get a `Source` if it's readable by the `User`."""
    return source


# TODO: Validate
@sources_router.patch("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by EditableSource.
def update_source(
    session: SessionDep,
    source: EditableSource,
    source_input: SourceUpdate,
) -> Source:
    """Update and return a `Source` if it's editable by the `User`."""
    return source_input.update(session, source)


# TODO: Validate
@sources_router.delete("/{source_id}")  # noqa: FAST003 - Used by EditableSource.
def delete_source(session: SessionDep, source: EditableSource) -> Message:
    """Delete a `Source` if it's editable by the `User`."""
    return delete_record(session, source)


router = APIRouter()
router.include_router(sources_router)
router.include_router(plugin_sources_router)
