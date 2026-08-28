# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Query, UploadFile

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.episodes.dependencies import ExistingEpisode
from app.schemas import Message, ReadOptions
from app.watches import services
from app.watches.dependencies import EditableWatch
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchesListOutput,
    WatchExportEntry,
    WatchImportInput,
    WatchImportResults,
    WatchOutput,
    WatchUpdate,
)
from app.watches.services import (
    delete_watches,
    export_watch_history_entries,
    get_watched_episodes,
    import_watch_history_file,
)

watches_router = APIRouter(prefix="/watches", tags=["watches"])


episode_watches_router = APIRouter(prefix="/episodes/{episode_id}", tags=["watches"])


# TODO: Validate
@episode_watches_router.post("/watches", response_model=WatchOutput)
def create_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode: ExistingEpisode,
    watch_input: WatchCreate,
) -> Watch:
    return services.create_watch(session, current_user.id, episode, watch_input)


# TODO: Validate
@watches_router.get("")
def get_watches(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> WatchesListOutput:
    """Get all of the `Watch`es for the `User`."""
    return get_watched_episodes(session, current_user, read_options)


# TODO: Validate
@watches_router.patch(
    "/{watch_id}",  # noqa: FAST003 - Used by UserWatch.
    response_model=WatchOutput,
)
def update_watch(
    session: SessionDep,
    watch: EditableWatch,
    watch_input: WatchUpdate,
) -> Watch:
    """Update a watch."""
    return services.update_watch(session, watch, watch_input)


# TODO: Validate
@watches_router.delete("/{watch_id}")  # noqa: FAST003 - Used by UserWatch.
def delete_watch(session: SessionDep, watch: EditableWatch) -> Message:
    """Delete a watch and all sibling watches by its id."""
    return delete_watches(session, watch)


# TODO: Add tests
# THis is under /watches and not /plugins because it does not use the plugin id for
# identification because it relies on the plugin itself and not it's database entry.
# TODO: Validate
@watches_router.post("/import")
def import_watch_history(
    file: UploadFile,
    # Parameters have to come from the query because the request body is the file.
    params: Annotated[WatchImportInput, Query()],
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchImportResults:
    """Import watch history from an uploaded file for a specific plugin."""
    return import_watch_history_file(session, current_user, file, params)


# TODO: Validate
@watches_router.get("/export")
def export_watch_history(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[WatchExportEntry]:
    """Export the `User`'s watches as a Stream Channeler watch history."""
    return export_watch_history_entries(session, current_user)


router = APIRouter()
router.include_router(watches_router)
router.include_router(episode_watches_router)
