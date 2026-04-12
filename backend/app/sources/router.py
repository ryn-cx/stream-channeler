from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import delete_record
from app.schemas import Message
from app.shows.models import Show
from app.shows.schemas import ShowOutput, ShowPostInput
from app.sources.dependencies import OwnedSource, ReadableSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
)

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/{source_id}", response_model=SourceOutput)  # noqa: FAST003 - Used by ReadableSource
def get_source(source: ReadableSource) -> Source:
    """Get a ``Source`` if it's readable by the current ``User``."""
    return source


@router.get("/{source_id}/shows", response_model=list[ShowOutput])  # noqa: FAST003 - Used by ReadableSource
def get_shows(source: ReadableSource) -> list[Show]:
    """List all ``Show``s for a ``Source`` if its ``Plugin`` is public or owned by the current ``User``."""
    return source.shows


@router.post("/{source_id}/shows", response_model=ShowOutput)  # noqa: FAST003 - Used by OwnedSource
def create_show(
    session: SessionDep,
    source: OwnedSource,
    show_input: ShowPostInput,
) -> Show:
    """Create a ``Show`` if the ``Source`` is owned by the current ``User``."""
    return show_input.create(session, Show, source)


@router.patch("/{source_id}", response_model=SourceOutput)  # noqa: FAST003 - Used by OwnedSource
def update_source(
    session: SessionDep,
    source: OwnedSource,
    source_input: SourcePatchInput,
) -> Source:
    """Update and return a ``Source`` if it's owned by the current ``User``."""
    return source_input.update(session, source)


@router.delete("/{source_id}")  # noqa: FAST003 - Used by OwnedSource
def delete_source(session: SessionDep, source: OwnedSource) -> Message:
    """Delete a ``Source`` if it's owned by the current ``User``."""
    return delete_record(session, source)
