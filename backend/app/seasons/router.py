from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeInput,
    EpisodeOutput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.media.service import create_record, delete_record, list_records, update_record
from app.models import Message
from app.seasons.dependencies import UserSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
)

router = APIRouter(prefix="/seasons", tags=["seasons"])


# FAST003 - Parameter is used by UserSeason.
@router.get("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003
def get_user_season(season: UserSeason) -> Season:
    """Get a season owned by the current user by its id."""
    return season


# FAST003 - Parameter is used by UserSeason.
@router.get("/{season_id}/episodes")  # noqa: FAST003
def get_user_season_episodes(
    session: SessionDep,
    season: UserSeason,
) -> EpisodesListOutput:
    """List all episodes for a season."""
    return list_records(
        session=session,
        parent=season,
        child_model=Episode,
        parent_key="season_id",
        list_output=EpisodesListOutput,
    )


# FAST003 - Parameter is used by UserSeason.
@router.post("/{season_id}/episodes", response_model=EpisodeOutput)  # noqa: FAST003
def create_user_episode(
    session: SessionDep,
    season: UserSeason,
    episode_input: EpisodePostInput,
) -> Episode:
    """Create an episode for a season."""
    return create_record(
        session=session,
        parent=season,
        post_input=episode_input,
        input_schema=EpisodeInput,
        existing=Episode.get(session, season, episode_input.key),
    )


# FAST003 - Parameter is used by UserSeason.
@router.patch("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003
def update_user_season(
    session: SessionDep,
    season: UserSeason,
    season_input: SeasonPatchInput,
) -> Season:
    """Update a season by its id."""
    return update_record(
        session=session,
        entry=season,
        body=season_input,
    )


# FAST003 - Parameter is used by UserSeason.
@router.delete("/{season_id}")  # noqa: FAST003
def delete_user_season(session: SessionDep, season: UserSeason) -> Message:
    """Delete a season by its id."""
    return delete_record(
        session=session,
        entry=season,
        model_name="Season",
    )
