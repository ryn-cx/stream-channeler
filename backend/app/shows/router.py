"""Show router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import (
    MediaOwner,
    build_table_columns,
    build_table_page,
    delete_record,
)
from app.plugins.models import Plugin
from app.schemas import Message
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
)
from app.shows.dependencies import OwnedShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowPublic,
    ShowTableOutput,
    ShowUpdate,
)
from app.sources.models import Source
from app.users.service import get_or_create_plugin_user

router = APIRouter(prefix="/shows", tags=["shows"])

# Every `ShowPublic` field is filterable and sortable; date columns also filter by range.
_TABLE_COLUMNS, _DATE_RANGE_COLUMNS = build_table_columns(Show, ShowPublic)


@router.get("")
def get_shows(  # noqa: PLR0913 - FastAPI query parameters
    session: SessionDep,
    current_user: CurrentUser,
    owner: MediaOwner | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100_000)] = 100,
    sorting: str | None = None,
    filters: str | None = None,
) -> ShowTableOutput:
    base = select(Show).join(Source).join(Plugin)
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
        tiebreaker=Show.id,
        offset=offset,
        limit=limit,
        sorting=sorting,
        filters=filters,
    )
    return ShowTableOutput(
        data=[ShowPublic.model_validate(row) for row in rows],
        count=count,
        server_side=server_side,
    )


@router.get("/{show_id}", response_model=ShowPublic)  # noqa: FAST003 - Used by ReadableShow
def get_show(show: ReadableShow) -> Show:
    """Get a `Show` if it's readable by the current `User`."""
    return show


@router.patch("/{show_id}", response_model=ShowPublic)  # noqa: FAST003 - Used by OwnedShow
def update_show(
    session: SessionDep,
    show: OwnedShow,
    show_input: ShowUpdate,
) -> Show:
    """Update and return a `Show` if it's owned by the current `User`."""
    return show_input.update(session, show)


@router.delete("/{show_id}")  # noqa: FAST003 - Used by OwnedShow.
def delete_show(session: SessionDep, show: OwnedShow) -> Message:
    """Delete a `Show` if it's owned by the current `User`."""
    return delete_record(session, show)


@router.post("/{show_id}/seasons", response_model=SeasonOutput)  # noqa: FAST003 - Used by OwnedShow
def create_season(
    session: SessionDep,
    show: OwnedShow,
    season_input: SeasonCreate,
) -> Season:
    """Create a `Season` if the `Show` is owned by the current `User`."""
    return season_input.create(session, Season, show)


@router.get("/{show_id}/seasons", response_model=list[SeasonOutput])  # noqa: FAST003 - Used by ReadableShow
def get_seasons(show: ReadableShow) -> list[Season]:
    """List all `Season`s for a `Show` if it's readable by the current `User`."""
    return show.seasons
