"""Episodes router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import OwnedEpisode, ReadableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
    EpisodesPublic,
    EpisodeUpdate,
)
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import OwnedSeason, ReadableSeason
from app.seasons.models import Season
from app.service import get_read_results
from app.shows.models import Show
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.service import get_or_create_plugin_user

episodes_router = APIRouter(prefix="/episodes", tags=["episodes"])


@episodes_router.get("")
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


@episodes_router.get("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by ReadableEpisode.
def get_episode(episode: ReadableEpisode) -> Episode:
    """Get an `Episode` if it's readable by the current `User`."""
    return episode


@episodes_router.patch("/{episode_id}", response_model=EpisodeOutput)  # noqa: FAST003 - Used by OwnedEpisode.
def update_episode(
    session: SessionDep,
    episode: OwnedEpisode,
    episode_input: EpisodeUpdate,
) -> Episode:
    """Update and return an `Episode` if it's owned by the current `User`."""
    return episode_input.update(session, episode)


@episodes_router.delete("/{episode_id}")  # noqa: FAST003 - Used by OwnedEpisode.
def delete_episode(session: SessionDep, episode: OwnedEpisode) -> Message:
    """Delete an `Episode` if it's owned by the current `User`."""
    return delete_record(session, episode)


season_episodes_router = APIRouter(prefix="/seasons/{season_id}", tags=["episodes"])


@season_episodes_router.post("/episodes", response_model=EpisodeOutput)
def create_episode(
    session: SessionDep,
    season: OwnedSeason,
    episode_input: EpisodeCreate,
) -> Episode:
    """Create an `Episode` if the `Season` is owned by the current `User`."""
    return episode_input.create(session, Episode, season)


@season_episodes_router.get("/episodes")
def get_season_episodes(
    session: SessionDep,
    season: ReadableSeason,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """List all `Episode`s for a `Season` if it's readable by the current `User`."""
    episode_selector = select(Episode).where(Episode.season_id == season.id)
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        episode_selector,
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


router = APIRouter()
router.include_router(episodes_router)
router.include_router(season_episodes_router)
