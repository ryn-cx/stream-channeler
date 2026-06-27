"""Source router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import (
    MediaOwner,
    build_table_columns,
    build_table_page,
    delete_record,
)
from app.plugins.models import Plugin
from app.schemas import Message
from app.shows.models import Show
from app.shows.schemas import ShowCreate, ShowPublic
from app.sources.dependencies import OwnedSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourcePublic,
    SourceTableOutput,
    SourceUpdate,
)
from app.users.service import get_or_create_plugin_user

router = APIRouter(prefix="/sources", tags=["sources"])

# Every `SourcePublic` field is filterable and sortable; date columns also filter by range.
_TABLE_COLUMNS, _DATE_RANGE_COLUMNS = build_table_columns(Source, SourcePublic)


@router.get("")
def get_sources(  # noqa: PLR0913 - FastAPI query parameters
    session: SessionDep,
    current_user: CurrentUser,
    owner: MediaOwner | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 100,
    sorting: str | None = None,
    filters: str | None = None,
) -> SourceTableOutput:
    base = select(Source).join(Plugin)
    if owner is None:
        base = base.where(Plugin.user_id == current_user.id)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        plugin_user = get_or_create_plugin_user(session=session)
        if owner == MediaOwner.official:
            base = base.where(Plugin.user_id == plugin_user.id)
        else:
            base = base.where(
                col(Plugin.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows, count, server_side = build_table_page(
        session,
        base,
        columns=_TABLE_COLUMNS,
        date_range_columns=_DATE_RANGE_COLUMNS,
        tiebreaker=Source.id,
        offset=offset,
        limit=limit,
        sorting=sorting,
        filters=filters,
    )
    return SourceTableOutput(
        data=[SourcePublic.model_validate(row) for row in rows],
        count=count,
        server_side=server_side,
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


@router.get("/{source_id}/shows", response_model=list[ShowPublic])  # noqa: FAST003 - Used by ReadableSource
def get_shows(source: ReadableSource) -> list[Show]:
    """Get all `Show`s for a `Source` if it's readable by the current `User`."""
    return source.shows
