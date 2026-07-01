"""Source router."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_list_response,
    media_owner_list_response,
)
from app.plugins.dependencies import EditablePlugin, ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.sources.dependencies import EditableSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
)
from app.users.dependencies import OptionalUser

plugin_sources_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["sources"])
sources_router = APIRouter(prefix="/sources", tags=["sources"])


@plugin_sources_router.post("/sources", response_model=SourcePublic)
def create_source(
    session: SessionDep,
    plugin: EditablePlugin,
    source_input: SourceCreate,
) -> Source:
    """Create a `Source` if the `Plugin` is editable by the `User`."""
    return source_input.create(session, Source, plugin)


@sources_router.get("")
def get_sources(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SourcesPublic:
    """Get all of the `Source`s readable by the `User`."""
    return media_owner_list_response(
        session=session,
        base=select(Source).join(Plugin),
        response_model=SourcesPublic,
        schema=SourcePublic,
        read_options=read_options,
        current_user=current_user,
    )


@plugin_sources_router.get("/sources")
def get_plugin_sources(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SourcesPublic:
    """Get all of the `Source`s for a `Plugin` if it is readable by the `User`."""
    base = select(Source).where(Source.plugin_id == plugin.id)
    return media_list_response(
        session=session,
        base=base,
        response_model=SourcesPublic,
        schema=SourcePublic,
        params=read_options,
        current_user=current_user,
    )


@sources_router.get("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by ReadableSource
def get_source(source: ReadableSource) -> Source:
    """Get a `Source` if it's readable by the `User`."""
    return source


@sources_router.patch("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by EditableSource
def update_source(
    session: SessionDep,
    source: EditableSource,
    source_input: SourceUpdate,
) -> Source:
    """Update and return a `Source` if it's editable by the `User`."""
    return source_input.update(session, source)


@sources_router.delete("/{source_id}")  # noqa: FAST003 - Used by EditableSource
def delete_source(session: SessionDep, source: EditableSource) -> Message:
    """Delete a `Source` if it's editable by the `User`."""
    return delete_record(session, source)


router = APIRouter()
router.include_router(sources_router)
router.include_router(plugin_sources_router)
