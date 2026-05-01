"""Source router."""

from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import delete_record
from app.schemas import Message
from app.shows.models import Show
from app.shows.schemas import ShowCreate, ShowPublic
from app.sources.dependencies import OwnedSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourcePublic,
    SourceUpdate,
)

router = APIRouter(prefix="/sources", tags=["sources"])


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
