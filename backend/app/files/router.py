"""Files router."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.files.dependencies import OwnedFile, ReadableFile
from app.files.schemas import FilePublic, FileUpdate
from app.media.service import delete_record
from app.plugins.models import File
from app.schemas import Message

router = APIRouter(
    prefix="/files",
    tags=["files"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by ReadableFile
def get_file(file: ReadableFile) -> File:
    """Get a `File` if it's readable by the current `User`."""
    return file


@router.patch("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by OwnedFile
def update_file(
    session: SessionDep,
    file: OwnedFile,
    file_input: FileUpdate,
) -> File:
    """Update and return a `File` if it's owned by the current `User`."""
    return file_input.update(session, file)


@router.delete("/{file_id}")  # noqa: FAST003 - Used by OwnedFile
def delete_file(session: SessionDep, file: OwnedFile) -> Message:
    """Delete a `File` if it's owned by the current `User`."""
    return delete_record(session, file)
