from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import create_record, delete_record, list_records, update_record
from app.models import Message
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInput,
    SeasonOutput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.dependencies import UserShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
)

router = APIRouter(prefix="/shows", tags=["shows"])


# FAST003 - Parameter is used by UserShow.
@router.get("/{show_id}", response_model=ShowOutput)  # noqa: FAST003
def get_user_show(show: UserShow) -> Show:
    """Get a show owned by the current user by its id."""
    return show


# FAST003 - Parameter is used by UserShow.
@router.get("/{show_id}/seasons", response_model=SeasonsListOutput)  # noqa: FAST003
def get_user_show_seasons(
    session: SessionDep,
    show: UserShow,
) -> SeasonsListOutput:
    """List all seasons for a show."""
    return list_records(
        session=session,
        parent=show,
        child_model=Season,
        parent_key="show_id",
        list_output=SeasonsListOutput,
    )


# FAST003 - Parameter is used by UserShow.
@router.post("/{show_id}/seasons", response_model=SeasonOutput)  # noqa: FAST003
def create_user_season(
    session: SessionDep,
    show: UserShow,
    season_input: SeasonPostInput,
) -> Season:
    """Create a season for a show."""
    return create_record(
        session=session,
        parent=show,
        post_input=season_input,
        input_schema=SeasonInput,
        existing=Season.get(session, show, season_input.key),
    )


# FAST003 - Parameter is used by UserShow.
@router.patch("/{show_id}", response_model=ShowOutput)  # noqa: FAST003
def update_user_show(
    session: SessionDep,
    show: UserShow,
    show_input: ShowPatchInput,
) -> Show:
    """Update a show by its id."""
    return update_record(
        session=session,
        entry=show,
        body=show_input,
    )


# FAST003 - Parameter is used by UserShow.
@router.delete("/{show_id}")  # noqa: FAST003
def delete_user_show(session: SessionDep, show: UserShow) -> Message:
    """Delete a show by its id."""
    return delete_record(
        session=session,
        entry=show,
        model_name="Show",
    )
