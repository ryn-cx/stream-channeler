from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import create_child, delete_record, list_children, update_record
from app.models import Message
from app.shows.models import Show
from app.shows.schemas import ShowOutput, ShowPostInput, ShowsListOutput
from app.sources.dependencies import ReadableSource, UserSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
)

router = APIRouter(prefix="/sources", tags=["sources"])


# FAST003 - Parameter is used by ReadableSource.
@router.get("/{source_id}", response_model=SourceOutput)  # noqa: FAST003
def get_user_source(source: ReadableSource) -> Source:
    """Get a source by its id if its plugin is public or owned by the current user."""
    return source


# FAST003 - Parameter is used by ReadableSource.
@router.get("/{source_id}/shows", response_model=ShowsListOutput)  # noqa: FAST003
def get_user_source_shows(
    session: SessionDep,
    source: ReadableSource,
) -> ShowsListOutput:
    """List all shows for a source if its plugin is public or owned by the current user."""
    return list_children(
        session,
        Show,
        "source_id",
        source.id,
        ShowOutput,
        ShowsListOutput,
    )


# FAST003 - Parameter is used by UserSource.
@router.post("/{source_id}/shows", response_model=ShowOutput)  # noqa: FAST003
def create_user_show(
    session: SessionDep,
    source: UserSource,
    show_input: ShowPostInput,
) -> Show:
    """Create a show for a source."""
    return create_child(session, Show, source, show_input, "source_id")


# FAST003 - Parameter is used by UserSource.
@router.patch("/{source_id}", response_model=SourceOutput)  # noqa: FAST003
def update_user_source(
    session: SessionDep,
    source: UserSource,
    source_input: SourcePatchInput,
) -> Source:
    """Update a source by its id."""
    return update_record(session, source, source_input)


# FAST003 - Parameter is used by UserSource.
@router.delete("/{source_id}")  # noqa: FAST003
def delete_user_source(session: SessionDep, source: UserSource) -> Message:
    """Delete a source by its id."""
    return delete_record(session, source)
