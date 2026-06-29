"""Show router."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaOwner, MediaReadOptions
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonCreate,
    SeasonOutput,
    SeasonsPublic,
)
from app.service import get_read_results
from app.shows.dependencies import OwnedShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowPublic,
    ShowsPublic,
    ShowUpdate,
)
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.service import get_or_create_plugin_user

router = APIRouter(prefix="/shows", tags=["shows"])


@router.get("")
def get_shows(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> ShowsPublic:
    base = select(Show).join(Source).join(Plugin)
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
        schema=ShowPublic,
        default_sort=Show.created_at,
        tiebreaker=Show.id,
        params=read_options,
        current_user=current_user,
    )
    return ShowsPublic(
        data=[ShowPublic.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
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


@router.get("/{show_id}/seasons")  # noqa: FAST003 - Used by ReadableShow
def get_seasons(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> SeasonsPublic:
    """List all `Season`s for a `Show` if it's readable by the current `User`."""
    base = select(Season).where(Season.show_id == show.id)
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
