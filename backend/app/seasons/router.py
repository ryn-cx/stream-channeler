# TODO: Validate
from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodePostInput,
    EpisodesListOutput,
)
from app.media.service import create_child, delete_record, list_children, update_record
from app.models import Message
from app.seasons.dependencies import ReadableSeason, UserSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPatchInput,
)

router = APIRouter(prefix="/seasons", tags=["seasons"])


# FAST003 - Parameter is used by ReadableSeason.
@router.get("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003
def get_user_season(season: ReadableSeason) -> Season:
    """Get a season by its id if its plugin is public or owned by the current user."""
    return season


# FAST003 - Parameter is used by ReadableSeason.
@router.get("/{season_id}/episodes")  # noqa: FAST003
def get_user_season_episodes(
    session: SessionDep,
    season: ReadableSeason,
) -> EpisodesListOutput:
    """List all episodes for a season if its plugin is public or owned by the current user."""
    return list_children(
        session,
        Episode,
        "season_id",
        season.id,
        EpisodeOutput,
        EpisodesListOutput,
    )


# FAST003 - Parameter is used by UserSeason.
@router.post("/{season_id}/episodes", response_model=EpisodeOutput)  # noqa: FAST003
def create_user_episode(
    session: SessionDep,
    season: UserSeason,
    episode_input: EpisodePostInput,
) -> Episode:
    """Create an episode for a season."""
    return create_child(session, Episode, season, episode_input, "season_id")


# FAST003 - Parameter is used by UserSeason.
@router.patch("/{season_id}", response_model=SeasonOutput)  # noqa: FAST003
def update_user_season(
    session: SessionDep,
    season: UserSeason,
    season_input: SeasonPatchInput,
) -> Season:
    """Update a season by its id."""
    return update_record(session, season, season_input)


# FAST003 - Parameter is used by UserSeason.
@router.delete("/{season_id}")  # noqa: FAST003
def delete_user_season(session: SessionDep, season: UserSeason) -> Message:
    """Delete a season by its id."""
    return delete_record(session, season)
