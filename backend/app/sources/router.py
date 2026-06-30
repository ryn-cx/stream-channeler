"""Source router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.dependencies import OwnedPlugin, ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import get_read_results
from app.sources.dependencies import OwnedSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceCreate,
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
)
from app.users.dependencies import OptionalUser
from app.users.service import get_or_create_plugin_user

sources_router = APIRouter(prefix="/sources", tags=["sources"])


@sources_router.get("")
def get_sources(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SourcesPublic:
    base = select(Source).join(Plugin)
    if read_options.owner is None:
        base = base.where(Plugin.user_id == current_user.id)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        plugin_user = get_or_create_plugin_user(session=session)
        if read_options.owner == MediaOwner.official:
            base = base.where(Plugin.user_id == plugin_user.id)
        else:
            base = base.where(
                col(Plugin.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=SourcePublic,
        default_sort=Source.created_at,
        tiebreaker=Source.id,
        params=read_options,
        current_user=current_user,
    )
    return SourcesPublic(
        data=[SourcePublic.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


@sources_router.get("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by ReadableSource
def get_source(source: ReadableSource) -> Source:
    """Get a `Source` if it's readable by the current `User`."""
    return source


@sources_router.patch("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by OwnedSource
def update_source(
    session: SessionDep,
    source: OwnedSource,
    source_input: SourceUpdate,
) -> Source:
    """Update and return a `Source` if it's owned by the current `User`."""
    return source_input.update(session, source)


@sources_router.delete("/{source_id}")  # noqa: FAST003 - Used by OwnedSource
def delete_source(session: SessionDep, source: OwnedSource) -> Message:
    """Delete a `Source` if it's owned by the current `User`."""
    return delete_record(session, source)


plugin_sources_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["sources"])


@plugin_sources_router.post("/sources", response_model=SourcePublic)
def create_source(
    session: SessionDep,
    plugin: OwnedPlugin,
    source_input: SourceCreate,
) -> Source:
    """Create a `Source` if the `Plugin` is owned by the current `User`."""
    return source_input.create(session, Source, plugin)


@plugin_sources_router.get("/sources")
def get_plugin_sources(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SourcesPublic:
    """List all `Source`s for a `Plugin` if it is public or owned by the current `User`."""
    base = select(Source).where(Source.plugin_id == plugin.id)
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=SourcePublic,
        default_sort=Source.created_at,
        tiebreaker=Source.id,
        params=read_options,
        current_user=current_user,
    )
    return SourcesPublic(
        data=[SourcePublic.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


router = APIRouter()
router.include_router(sources_router)
router.include_router(plugin_sources_router)
