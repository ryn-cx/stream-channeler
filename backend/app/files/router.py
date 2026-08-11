# TODO: Validate
"""Files router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.files.dependencies import EditableFile, ReadableFile
from app.files.models import File
from app.files.schemas import (
    FileCreate,
    FileListPublic,
    FilePublic,
    FilesPublic,
    FileUpdate,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.plugins.dependencies import EditablePlugin, ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.users.models import User

files_router = APIRouter(
    prefix="/admin/files",
    tags=["files"],
    dependencies=[Depends(get_current_active_superuser)],
)
plugin_files_router = APIRouter(
    prefix="/admin/plugins/{plugin_id}",
    tags=["files"],
    dependencies=[Depends(get_current_active_superuser)],
)

FILE_PARENT_COLUMNS: dict[str, Any] = {
    "plugin_name": Plugin.name,
    "username": User.username,
}


# TODO: Validate
@plugin_files_router.post("/files", response_model=FilePublic)
def create_file(
    session: SessionDep,
    plugin: EditablePlugin,
    file_input: FileCreate,
) -> File:
    """Create a `File` if the `Plugin` is editable by the `User`."""
    return file_input.create(session, File, plugin)


# TODO: Validate
@files_router.get("")
def get_files(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> FilesPublic:
    """Get every `File` across all `Plugin`s readable by the `User`."""
    return media_scoped_list_response(
        session=session,
        base=File.select_with_user_eager(),
        response_model=FilesPublic,
        schema=FileListPublic,
        read_options=read_options,
        current_user=current_user,
        extra_columns=FILE_PARENT_COLUMNS,
    )


# TODO: Validate
@plugin_files_router.get("/files")
def get_plugin_files(
    plugin: ReadablePlugin,
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> FilesPublic:
    """List all `File`s for a `Plugin` if it is public or editable by the `User`."""
    base = File.select_with_user_eager().where(File.plugin_id == plugin.id)
    return list_response(
        session=session,
        base=base,
        response_model=FilesPublic,
        schema=FileListPublic,
        params=read_options,
        extra_columns=FILE_PARENT_COLUMNS,
        current_user=current_user,
    )


# TODO: Validate
@files_router.get("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by ReadableFile.
def get_file(file: ReadableFile) -> File:
    """Get a `File` if it's readable by the `User`."""
    return file


# TODO: Validate
@files_router.patch("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by EditableFile.
def update_file(
    session: SessionDep,
    file: EditableFile,
    file_input: FileUpdate,
) -> File:
    """Update and return a `File` if it's editable by the `User`."""
    return file_input.update(session, file)


# TODO: Validate
@files_router.delete("/{file_id}")  # noqa: FAST003 - Used by EditableFile.
def delete_file(session: SessionDep, file: EditableFile) -> Message:
    """Delete a `File` if it's editable by the `User`."""
    return delete_record(session, file)


router = APIRouter()
router.include_router(files_router)
router.include_router(plugin_files_router)
