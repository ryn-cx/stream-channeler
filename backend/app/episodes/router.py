"""Episodes router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.episodes.dependencies import OwnedEpisode, ReadableEpisode
from app.episodes.models import Episode
from app.episodes.schemas import (
    EpisodeOutput,
    EpisodeTableOutput,
    EpisodeUpdate,
)
from app.media.service import (
    MediaOwner,
    build_table_columns,
    build_table_page,
    delete_record,
)
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user
from app.watches.schemas import (
    WatchCreate,
    WatchOutput,
)
from app.watches.services import create_watches

router = APIRouter(prefix="/episodes", tags=["episodes"])

# Every `EpisodeOutput` field is filterable and sortable; date columns also filter by range.
_TABLE_COLUMNS, _DATE_RANGE_COLUMNS = build_table_columns(Episode, EpisodeOutput)


@router.get("")
def get_episodes(  # noqa: PLR0913 - FastAPI query parameters
    session: SessionDep,
    current_user: CurrentUser,
    owner: MediaOwner | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 100,
    sorting: str | None = None,
    filters: str | None = None,
) -> EpisodeTableOutput:
    base = select(Episode).join(Season).join(Show).join(Source).join(Plugin)
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
        tiebreaker=Episode.id,
        offset=offset,
        limit=limit,
        sorting=sorting,
        filters=filters,
    )
    return EpisodeTableOutput(
        data=[EpisodeOutput.model_validate(row) for row in rows],
        count=count,
        server_side=server_side,
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
