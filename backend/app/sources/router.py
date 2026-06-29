"""Source router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import get_read_results
from app.shows.models import Show
from app.shows.schemas import ShowCreate, ShowPublic, ShowsPublic
from app.sources.dependencies import OwnedSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourcePublic,
    SourcesPublic,
    SourceUpdate,
)
from app.users.dependencies import OptionalUser
from app.users.service import get_or_create_plugin_user

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("")
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


@router.get("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by ReadableSource
def get_source(source: ReadableSource) -> Source:
    """Get a `Source` if it's readable by the current `User`."""
    return source


@router.patch("/{source_id}", response_model=SourcePublic)  # noqa: FAST003 - Used by OwnedSource
def update_source(
    session: SessionDep,
    source: OwnedSource,
    source_input: SourceUpdate,
) -> Source:
    """Update and return a `Source` if it's owned by the current `User`."""
    return source_input.update(session, source)


@router.delete("/{source_id}")  # noqa: FAST003 - Used by OwnedSource
def delete_source(session: SessionDep, source: OwnedSource) -> Message:
    """Delete a `Source` if it's owned by the current `User`."""
    return delete_record(session, source)


@router.post("/{source_id}/shows", response_model=ShowPublic)  # noqa: FAST003 - Used by OwnedSource
def create_show(
    session: SessionDep,
    source: OwnedSource,
    show_input: ShowCreate,
) -> Show:
    """Create a `Show` if the `Source` is owned by the current `User`."""
    return show_input.create(session, Show, source)


@router.get("/{source_id}/shows")  # noqa: FAST003 - Used by ReadableSource
def get_shows(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get all `Show`s for a `Source` if it's readable by the current `User`."""
    base = select(Show).where(Show.source_id == source.id)
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=ShowPublic,
        default_sort=Show.created_at,
        tiebreaker=Show.id,
        params=read_options,
        current_user=current_user,
    )
    return ShowsPublic(
        data=[ShowPublic.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )
