"""Episodes router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import OwnedEpisode, ReadableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodesPublic,
    EpisodeUpdate,
)
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.service import get_read_results
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from app.watches.schemas import (
    WatchCreate,
    WatchOutput,
)
from app.watches.services import create_watches

router = APIRouter(prefix="/episodes", tags=["episodes"])


@router.get("")
def get_episodes(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> EpisodesPublic:
    base = select(Episode).join(Season).join(Show).join(Source).join(Plugin)
    if read_options.owner is None:
        base = base.where(Plugin.user_id == current_user.id)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        plugin_user = get_or_create_plugin_user(session=session)
        if read_options.owner == MediaOwner.official:
            base = base.where(Plugin.user_id == plugin_user.id)
        else:
            base = base.where(
                col(Plugin.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=EpisodeOutput,
        default_sort=Episode.created_at,
        tiebreaker=Episode.id,
        params=read_options,
        current_user=current_user,
    )
    return EpisodesPublic(
        data=[EpisodeOutput.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


@router.get("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by ReadableEpisode.
def get_episode(episode: ReadableEpisode) -> Episode:
    """Get an `Episode` if it's readable by the current `User`."""
    return episode


@router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by OwnedEpisode.
def update_episode(
    session: SessionDep,
    episode: OwnedEpisode,
    episode_input: EpisodeUpdate,
) -> Episode:
    """Update and return an `Episode` if it's owned by the current `User`."""
    return episode_input.update(session, episode)


@router.delete("/{episode_id}")  # noqa: FAST003 - Used by OwnedEpisode.
def delete_episode(session: SessionDep, episode: OwnedEpisode) -> Message:
    """Delete an `Episode` if it's owned by the current `User`."""
    return delete_record(session, episode)


@router.post("/{episode_id}/watches")  # noqa: FAST003 - Used by ReadableEpisode.
def create_watch(
    session: SessionDep,
    current_user: CurrentUser,
    episode: ReadableEpisode,
    watch_input: WatchCreate,
) -> list[WatchOutput]:
    """Create a `Watch` if the `Episode` is owned by the current `User`."""
    return create_watches(session, current_user.id, episode, watch_input)
