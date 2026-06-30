# TODO: Validate
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import ReadableEpisode
from app.schemas import Message
from app.watches.dependencies import OwnedWatch
from app.watches.models import Watch
from app.watches.schemas import (
    WatchCreate,
    WatchesListOutput,
    WatchImportInput,
    WatchImportResults,
    WatchOutput,
    WatchUpdate,
)
from app.watches.services import (
    create_watches,
    delete_watches,
    get_installed_plugin,
    get_watched_episodes,
    sync_episode_watches,
    update_watches,
)

watches_router = APIRouter(prefix="/watches", tags=["watches"])

episode_watches_router = APIRouter(prefix="/episodes/{episode_id}", tags=["watches"])


@episode_watches_router.post("/watches")
def create_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode: ReadableEpisode,
    watch_input: WatchCreate,
) -> list[WatchOutput]:
    """Create a `Watch` if the `Episode` is owned by the current `User`."""
    return create_watches(session, current_user.id, episode, watch_input)


@watches_router.get("")
def get_watches(
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchesListOutput:
    """Get multiple watched episode records."""
    return get_watched_episodes(session, current_user.id)


@watches_router.get("/{watch_id}", response_model=WatchOutput)  # noqa: FAST003 - Used by UserWatch.
def get_watch(watch: OwnedWatch) -> Watch:
    """Get a watch owned by the current user by its id."""
    return watch


@watches_router.patch("/{watch_id}")  # noqa: FAST003 - Used by UserWatch.
def update_watch(
    session: SessionDep,
    watch: OwnedWatch,
    watch_input: WatchUpdate,
) -> list[WatchOutput]:
    """Update a watch and all matching sibling watches."""
    return update_watches(session, watch, watch_input)


@watches_router.delete("/{watch_id}")  # noqa: FAST003 - Used by UserWatch.
def delete_watch(session: SessionDep, watch: OwnedWatch) -> Message:
    """Delete a watch and all sibling watches by its id."""
    return delete_watches(session, watch)


@watches_router.post("/sync")
def sync_watches(
    session: SessionDep,
    current_user: CurrentUser,
) -> Message:
    """Sync watches across episodes with the same key within the same plugin."""
    return sync_episode_watches(session, current_user.id)


# TODO: Add tests
# THis is under /watches and not /plugins because it does not use the plugin id for
# identification because it relies on the plugin itself and not it's database entry.
@watches_router.post("/import")
def import_watch_history(
    file: UploadFile,
    # Parameters have to come from the query because the request body is the file.
    params: Annotated[WatchImportInput, Query()],
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchImportResults:
    """Import watch history from an uploaded file for a specific plugin."""
    plugin = get_installed_plugin(params.plugin_key)
    if not plugin:
        raise HTTPException(
            status_code=404,
            detail=f"Plugin '{params.plugin_key}' not found.",
        )
    if not plugin.implements("import_watch_history_instructions"):
        raise HTTPException(
            status_code=422,
            detail=f"Plugin '{params.plugin_key}' does not support watch history import.",
        )

    content = file.file.read().decode("utf-8")

    plugin_instance = plugin(session=session)
    result = plugin_instance.import_watch_history(
        content=content,
        user=current_user,
        new_only=params.new_only,
        verified=params.verified,
    )
    session.commit()
    return result


router = APIRouter()
router.include_router(watches_router)
router.include_router(episode_watches_router)
