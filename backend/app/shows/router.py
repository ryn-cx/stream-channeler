from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import create_child, delete_record, list_children, update_record
from app.models import Message
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPostInput,
    SeasonsListOutput,
)
from app.shows.dependencies import ReadableShow, UserShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
)

router = APIRouter(prefix="/shows", tags=["shows"])


# FAST003 - Parameter is used by ReadableShow.
@router.get("/{show_id}", response_model=ShowOutput)  # noqa: FAST003
def get_user_show(show: ReadableShow) -> Show:
    """Get a show by its id if its plugin is public or owned by the current user."""
    return show


# FAST003 - Parameter is used by ReadableShow.
@router.get("/{show_id}/seasons", response_model=SeasonsListOutput)  # noqa: FAST003
def get_user_show_seasons(
    session: SessionDep,
    show: ReadableShow,
) -> SeasonsListOutput:
    """List all seasons for a show if its plugin is public or owned by the current user."""
    return list_children(
        session,
        Season,
        "show_id",
        show.id,
        SeasonOutput,
        SeasonsListOutput,
    )


# FAST003 - Parameter is used by UserShow.
@router.post("/{show_id}/seasons", response_model=SeasonOutput)  # noqa: FAST003
def create_user_season(
    session: SessionDep,
    show: UserShow,
    season_input: SeasonPostInput,
) -> Season:
    """Create a season for a show."""
    return create_child(session, Season, show, season_input, "show_id")


# FAST003 - Parameter is used by UserShow.
@router.patch("/{show_id}", response_model=ShowOutput)  # noqa: FAST003
def update_user_show(
    session: SessionDep,
    show: UserShow,
    show_input: ShowPatchInput,
) -> Show:
    """Update a show by its id."""
    return update_record(session, show, show_input)


# FAST003 - Parameter is used by UserShow.
@router.delete("/{show_id}")  # noqa: FAST003
def delete_user_show(session: SessionDep, show: UserShow) -> Message:
    """Delete a show by its id."""
    return delete_record(session, show)
