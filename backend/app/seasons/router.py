"""Season router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
    EpisodesPublic,
)
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.dependencies import OwnedSeason, ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonsPublic,
    SeasonUpdate,
)
from app.service import get_read_results
from app.shows.models import Show
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.service import get_or_create_plugin_user

router = APIRouter(prefix="/seasons", tags=["seasons"])


@router.get("")
def get_seasons(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> SeasonsPublic:
    base = select(Season).join(Show).join(Source).join(Plugin)
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
        schema=SeasonOutput,
        default_sort=Season.created_at,
        tiebreaker=Season.id,
        params=read_options,
        current_user=current_user,
    )
    return SeasonsPublic(
        data=[SeasonOutput.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


@router.get("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003 - Used by ReadableSeason
def get_season(season: ReadableSeason) -> Season:
    """Get a `Season` if it's readable by the current `User`."""
    return season


@router.patch("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003 - Used by OwnedSeason
def update_season(
    session: SessionDep,
    season: OwnedSeason,
    season_input: SeasonUpdate,
) -> Season:
    """Update and return a `Season` if it's owned by the current `User`."""
    return season_input.update(session, season)


@router.delete("/{season_id}")  # noqa: FAST003 - Used by OwnedSeason
def delete_season(session: SessionDep, season: OwnedSeason) -> Message:
    """Delete a `Season` if it's owned by the current `User`."""
    return delete_record(session, season)


@router.post("/{season_id}/episodes", response_model=EpisodeOutput)  # noqa: FAST003 - Used by OwnedSeason
def create_episode(
    session: SessionDep,
    season: OwnedSeason,
    episode_input: EpisodeCreate,
) -> Episode:
    """Create an `Episode` if the `Season` is owned by the current `User`."""
    return episode_input.create(session, Episode, season)


@router.get("/{season_id}/episodes")  # noqa: FAST003 - Used by ReadableSeason
def get_episodes(
    session: SessionDep,
    season: ReadableSeason,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> EpisodesPublic:
    """List all `Episode`s for a `Season` if it's readable by the current `User`."""
    base = select(Episode).where(Episode.season_id == season.id)
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
