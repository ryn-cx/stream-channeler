"""Season router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeCreate,
    EpisodeOutput,
)
from app.media.service import (
    MediaOwner,
    build_table_columns,
    build_table_page,
    delete_record,
)
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.dependencies import OwnedSeason, ReadableSeason
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonTableOutput,
    SeasonUpdate,
)
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user

router = APIRouter(prefix="/seasons", tags=["seasons"])

# Every `SeasonOutput` field is filterable and sortable; date columns also filter by range.
_TABLE_COLUMNS, _DATE_RANGE_COLUMNS = build_table_columns(Season, SeasonOutput)


@router.get("")
def get_seasons(  # noqa: PLR0913 - FastAPI query parameters
    session: SessionDep,
    current_user: CurrentUser,
    owner: MediaOwner | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 100,
    sorting: str | None = None,
    filters: str | None = None,
) -> SeasonTableOutput:
    base = select(Season).join(Show).join(Source).join(Plugin)
    if owner is None:
        base = base.where(Plugin.user_id == current_user.id)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        plugin_user = get_or_create_plugin_user(session=session)
        if owner == MediaOwner.official:
            base = base.where(Plugin.user_id == plugin_user.id)
        else:
            base = base.where(
                col(Plugin.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows, count, server_side = build_table_page(
        session,
        base,
        columns=_TABLE_COLUMNS,
        date_range_columns=_DATE_RANGE_COLUMNS,
        tiebreaker=Season.id,
        offset=offset,
        limit=limit,
        sorting=sorting,
        filters=filters,
    )
    return SeasonTableOutput(
        data=[SeasonOutput.model_validate(row) for row in rows],
        count=count,
        server_side=server_side,
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


@router.get("/{season_id}/episodes", response_model=list[EpisodeOutput])  # noqa: FAST003 - Used by ReadableSeason
def get_episodes(season: ReadableSeason) -> list[Episode]:
    """List all `Episode`s for a `Season` if it's readable by the current `User`."""
    return season.episodes
