# TODO: Validate


"""Source router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.media.service import delete_record
from app.plugins.dependencies import ExistingPlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.sources.dependencies import ExistingSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourceListPublic,
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
)
from app.users.dependencies import OptionalUser

sources_router = APIRouter(
    prefix="/sources",
    tags=["sources"],
    dependencies=[Depends(get_current_active_superuser)],
)


plugin_sources_router = APIRouter(
    prefix="/plugins/{plugin_id}",
    tags=["sources"],
    dependencies=[Depends(get_current_active_superuser)],
)


SOURCE_EXTRA_COLUMNS: dict[str, Any] = {
    "plugin_name": Plugin.name,
}


# TODO: Validate
@plugin_sources_router.post("/sources", response_model=SourcePublic)
def create_source(
    session: SessionDep,
    plugin: ExistingPlugin,
    source_input: SourceCreate,
) -> Source:
    return source_input.create(session, Source, plugin)


# TODO: Validate
@sources_router.get("")
def get_sources(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SourcesPublic:
    """Get `Source`s."""
    return list_response(
        session=session,
        base=Source.select_with_plugin_eager(),
        response_model=SourcesPublic,
        schema=SourceListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SOURCE_EXTRA_COLUMNS,
    )


# TODO: Validate
@plugin_sources_router.get("/sources")
def get_plugin_sources(
    session: SessionDep,
    plugin: ExistingPlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SourcesPublic:
    return list_response(
        session=session,
        base=Source.select_with_plugin_eager().where(Source.plugin_id == plugin.id),
        response_model=SourcesPublic,
        schema=SourceListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SOURCE_EXTRA_COLUMNS,
    )


# TODO: Validate
@sources_router.get("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by ExistingSource.
def get_source(source: ExistingSource) -> Source:
    return source


# TODO: Validate
@sources_router.patch("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by ExistingSource.
def update_source(
    session: SessionDep,
    source: ExistingSource,
    source_input: SourceUpdate,
) -> Source:
    return source_input.update(session, source)


# TODO: Validate
@sources_router.delete("/{source_id}")  # noqa: FAST003 - Used by ExistingSource.
def delete_source(session: SessionDep, source: ExistingSource) -> Message:
    return delete_record(session, source)


router = APIRouter()
router.include_router(sources_router)
router.include_router(plugin_sources_router)
