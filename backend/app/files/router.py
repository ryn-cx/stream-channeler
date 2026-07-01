"""Files router."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.files.dependencies import EditableFile, ReadableFile
from app.files.schemas import FilePublic, FileUpdate
from app.media.service import delete_record
from app.plugins.models import File
from app.schemas import Message

router = APIRouter(
    prefix="/admin/files",
    tags=["files"],
    dependencies=[Depends(get_current_active_superuser)],
)


@router.get("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by ReadableFile
def get_file(file: ReadableFile) -> File:
    """Get a `File` if it's readable by the `User`."""
    return file


@router.patch("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by EditableFile
def update_file(
    session: SessionDep,
    file: EditableFile,
    file_input: FileUpdate,
) -> File:
    """Update and return a `File` if it's editable by the `User`."""
    return file_input.update(session, file)


@router.delete("/{file_id}")  # noqa: FAST003 - Used by EditableFile
def delete_file(session: SessionDep, file: EditableFile) -> Message:
    """Delete a `File` if it's editable by the `User`."""
    return delete_record(session, file)
