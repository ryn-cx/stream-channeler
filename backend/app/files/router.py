# TODO: Validate
"""Files router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.files.dependencies import ExistingFile
from app.files.models import File
from app.files.schemas import (
    FileCreate,
    FileListPublic,
    FilePublic,
    FilesPublic,
    FileUpdate,
)
from app.media.service import delete_record
from app.plugins.dependencies import ExistingPlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response

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
}


# TODO: Validate
@plugin_files_router.post("/files", response_model=FilePublic)
def create_file(
    session: SessionDep,
    plugin: ExistingPlugin,
    file_input: FileCreate,
) -> File:
    return file_input.create(session, File, plugin)


# TODO: Validate
@files_router.get("")
def get_files(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> FilesPublic:
    return list_response(
        session=session,
        base=File.select_with_plugin_eager(),
        response_model=FilesPublic,
        schema=FileListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=FILE_PARENT_COLUMNS,
    )


# TODO: Validate
@plugin_files_router.get("/files")
def get_plugin_files(
    plugin: ExistingPlugin,
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> FilesPublic:
    base = File.select_with_plugin_eager().where(File.plugin_id == plugin.id)
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
@files_router.get("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by ExistingFile.
def get_file(file: ExistingFile) -> File:
    return file


# TODO: Validate
@files_router.patch("/{file_id}", response_model=FilePublic)  # noqa: FAST003 - Used by ExistingFile.
def update_file(
    session: SessionDep,
    file: ExistingFile,
    file_input: FileUpdate,
) -> File:
    return file_input.update(session, file)


# TODO: Validate
@files_router.delete("/{file_id}")  # noqa: FAST003 - Used by ExistingFile.
def delete_file(session: SessionDep, file: ExistingFile) -> Message:
    return delete_record(session, file)


router = APIRouter()
router.include_router(files_router)
router.include_router(plugin_files_router)
