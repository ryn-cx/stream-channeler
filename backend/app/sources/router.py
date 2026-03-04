from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import create_record, delete_record, list_records, update_record
from app.models import Message
from app.shows.models import Show
from app.shows.schemas import ShowInput, ShowOutput, ShowPostInput, ShowsListOutput
from app.sources.dependencies import UserSource
from app.sources.models import Source
from app.sources.schemas import (
    SourceOutput,
    SourcePatchInput,
)

router = APIRouter(prefix="/sources", tags=["sources"])


# FAST003 - Parameter is used by UserSource.
@router.get("/{source_id}", response_model=SourceOutput)  # noqa: FAST003
def get_user_source(source: UserSource) -> Source:
    """Get a source owned by the current user by its id."""
    return source


# FAST003 - Parameter is used by UserSource.
@router.get("/{source_id}/shows", response_model=ShowsListOutput)  # noqa: FAST003
def get_user_source_shows(
    session: SessionDep,
    source: UserSource,
) -> ShowsListOutput:
    """List all shows for a source."""
    return list_records(
        session=session,
        parent=source,
        child_model=Show,
        parent_key="source_id",
        list_output=ShowsListOutput,
    )


# FAST003 - Parameter is used by UserSource.
@router.post("/{source_id}/shows", response_model=ShowOutput)  # noqa: FAST003
def create_user_show(
    session: SessionDep,
    source: UserSource,
    show_input: ShowPostInput,
) -> Show:
    """Create a show for a source."""
    return create_record(
        session=session,
        parent=source,
        post_input=show_input,
        input_schema=ShowInput,
        existing=Show.get(session, source, show_input.key),
    )


# FAST003 - Parameter is used by UserSource.
@router.patch("/{source_id}", response_model=SourceOutput)  # noqa: FAST003
def update_user_source(
    session: SessionDep,
    source: UserSource,
    source_input: SourcePatchInput,
) -> Source:
    """Update a source by its id."""
    return update_record(
        session=session,
        entry=source,
        body=source_input,
    )


# FAST003 - Parameter is used by UserSource.
@router.delete("/{source_id}")  # noqa: FAST003
def delete_user_source(session: SessionDep, source: UserSource) -> Message:
    """Delete a source by its id."""
    return delete_record(
        session=session,
        entry=source,
        model_name="Source",
    )
