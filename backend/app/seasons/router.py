"""Season router."""

from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
)
from app.media.service import delete_record
from app.schemas import Message
from app.seasons.dependencies import OwnedSeason, ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonUpdate,
)

router = APIRouter(prefix="/seasons", tags=["seasons"])


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


@router.get("/{season_id}/episodes", response_model=list[EpisodeOutput])  # noqa: FAST003 - Used by ReadableSeason
def get_episodes(season: ReadableSeason) -> list[Episode]:
    """List all `Episode`s for a `Season` if it's readable by the current `User`."""
    return season.episodes
