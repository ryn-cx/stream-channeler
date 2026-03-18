from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.auth.dependencies import CurrentUser, SessionDep
from app.models import Message
from app.watches.dependencies import UserWatch
from app.watches.models import Watch
from app.watches.schemas import (
    WatchesListOutput,
    WatchImportInput,
    WatchImportPluginsOutput,
    WatchImportResults,
    WatchOutput,
    WatchPatchInput,
)
from app.watches.services import (
    delete_watches,
    get_importable_plugins,
    get_installed_plugin,
    get_watched_episodes,
    sync_episode_watches,
    update_watches,
)

router = APIRouter(prefix="/watches", tags=["watches"])


# FAST003 - Parameter is used by UserWatch.
@router.get("/{watch_id}", response_model=WatchOutput)  # noqa: FAST003
def get_user_watch(watch: UserWatch) -> Watch:
    """Get a watch owned by the current user by its id."""
    return watch


@router.get("")
def get_user_watches(
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchesListOutput:
    """Get multiple watched episode entries."""
    return get_watched_episodes(session, current_user.id)


@router.post("/sync")
def sync_watches(
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    """Sync watches across episodes with the same key within the same plugin."""
    return sync_episode_watches(session, current_user.id)


# FAST003 - Parameter is used by UserWatch.
@router.patch("/{watch_id}")  # noqa: FAST003
def update_user_watch(
    session: SessionDep,
    watch: UserWatch,
    watch_input: WatchPatchInput,
) -> list[WatchOutput]:
    """Update a watch and all matching sibling watches."""
    return update_watches(session, watch, watch_input)


# FAST003 - Parameter is used by UserWatch.
@router.delete("/{watch_id}")  # noqa: FAST003
def delete_user_watch(session: SessionDep, watch: UserWatch) -> Message:
    """Delete a watch and all sibling watches by its id."""
    return delete_watches(session, watch)


# TODO: Add tests
@router.get("/import/plugins")
def list_importable_plugins(_current_user: CurrentUser) -> WatchImportPluginsOutput:
    """List all plugins that support importing watch history."""
    return WatchImportPluginsOutput(
        plugins=[
            plugin.import_watch_history_info() for plugin in get_importable_plugins()
        ],
    )


# TODO: Add tests
@router.post("/import")
def import_watch_history(
    file: UploadFile,
    # Parameters have to come from the query because the request body is the file.
    params: Annotated[WatchImportInput, Query()],
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchImportResults:
    """Import watch history from an uploaded file for a specific plugin."""
    if not (plugin := get_installed_plugin(params.plugin_key)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Plugin '{params.plugin_key}' does not support watch import.",
        )

    content = file.file.read().decode("utf-8")

    plugin_instance = plugin(db=session)
    result = plugin_instance.import_watch_history(
        content=content,
        user=current_user,
        new_only=params.new_only,
        verified=params.verified,
    )
    session.commit()
    return result
