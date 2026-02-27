# TODO: Validate

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, UploadFile, status

from app.auth.dependencies import CurrentUser, SessionDep
from app.constants import MAX_ENTRIES_PER_PAGE
from app.media.dependencies import ExistingEpisode, ExistingEpisodeWatch
from app.media.models import EpisodeWatch
from app.media.schemas import (
    EpisodeWatchPatchInput,
    EpisodeWatchPostInput,
    SingleEpisodeWatchOutput,
    WatchedEpisodesOutput,
    WatchImportInput,
    WatchImportPluginsOutput,
    WatchImportResult,
)
from app.media.services import get_importable_plugins, get_plugin, save_episode_watch
from app.media.services import get_watched_episodes as get_watched_episodes_service
from app.models import Message

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.post("/watches")
def post_watched_episode(
    session: SessionDep,
    current_user: CurrentUser,
    watch_input: EpisodeWatchPostInput,
    episode: ExistingEpisode,
) -> SingleEpisodeWatchOutput:
    """Create a new episode watch entry."""
    episode_watch = EpisodeWatch(
        user_id=current_user.id,
        episode_id=watch_input.episode_id,
    )
    session.add(episode_watch)

    return save_episode_watch(
        session,
        episode_watch,
        episode,
        watch_input,
    )


# FAST003 - Parameter is used by EpisodeWatchDep
@router.patch("/watches/{episode_watch_id}")  # noqa: FAST003
def patch_watched_episode(
    session: SessionDep,
    episode_watch: ExistingEpisodeWatch,
    watch_input: EpisodeWatchPatchInput,
) -> SingleEpisodeWatchOutput:
    """Update an existing episode watch entry."""
    return save_episode_watch(
        session,
        episode_watch,
        episode_watch.episode,
        watch_input,
    )


# FAST003 - Parameter is used by EpisodeWatchDep
@router.delete("/watches/{episode_watch_id}")  # noqa: FAST003
def delete_watched_episode(
    session: SessionDep,
    episode_watch: ExistingEpisodeWatch,
) -> Message:
    """Delete an existing episode watch entry."""
    session.delete(episode_watch)
    session.commit()
    return Message(message="Episode watch deleted")


@router.get("/watches")
def get_watched_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = MAX_ENTRIES_PER_PAGE,
) -> WatchedEpisodesOutput:
    """Get multiple watched episode entries."""
    return get_watched_episodes_service(session, current_user.id, skip, limit)


@router.get("/watches/import/plugins")
def list_importable_plugins(_current_user: CurrentUser) -> WatchImportPluginsOutput:
    """List all plugins that support importing watch history."""
    return WatchImportPluginsOutput(
        plugins=[
            plugin.import_watch_history_info() for plugin in get_importable_plugins()
        ],
    )


@router.post("/watches/import")
def import_watch_history(
    file: UploadFile,
    params: Annotated[WatchImportInput, Query()],
    session: SessionDep,
    current_user: CurrentUser,
) -> WatchImportResult:
    """Import watch history from an uploaded file for a specific plugin."""
    if not (plugin := get_plugin(params.plugin_id)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Plugin '{params.plugin_id}' does not support watch import.",
        )

    content_bytes = file.file.read()
    content = content_bytes.decode("utf-8")

    plugin_instance = plugin(db=session)
    result = plugin_instance.import_watch_history(
        content=content,
        user=current_user,
        new_only=params.new_only,
        verified=params.verified,
    )
    session.commit()
    return result
