from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.media.service import delete_record
from app.schemas import Message
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonOutput,
    SeasonPostInput,
)
from app.shows.dependencies import OwnedShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowOutput,
    ShowPatchInput,
)

router = APIRouter(prefix="/shows", tags=["shows"])


@router.get("/{show_id}", response_model=ShowOutput)  # noqa: FAST003 - Used by ReadableShow
def get_show(show: ReadableShow) -> Show:
    """Get a ``Show`` if it's readable by the current ``User``."""
    return show


@router.get("/{show_id}/seasons", response_model=list[SeasonOutput])  # noqa: FAST003 - Used by ReadableShow
def get_seasons(show: ReadableShow) -> list[Season]:
    """List all ``Season``s for a ``Show`` if its ``Plugin`` is public or owned by the current ``User``."""
    return show.seasons


@router.post("/{show_id}/seasons", response_model=SeasonOutput)  # noqa: FAST003 - Used by OwnedShow
def create_season(
    session: SessionDep,
    show: OwnedShow,
    season_input: SeasonPostInput,
) -> Season:
    """Create a ``Season`` if the ``Show`` is owned by the current ``User``."""
    return season_input.create(session, Season, show)


@router.patch("/{show_id}", response_model=ShowOutput)  # noqa: FAST003 - Used by OwnedShow
def update_show(
    session: SessionDep,
    show: OwnedShow,
    show_input: ShowPatchInput,
) -> Show:
    """Update and return a ``Show`` if it's owned by the current ``User``."""
    return show_input.update(session, show)


@router.delete("/{show_id}")  # noqa: FAST003 - Used by OwnedShow.
def delete_show(session: SessionDep, show: OwnedShow) -> Message:
    """Delete a ``Show`` if it's owned by the current ``User``."""
    return delete_record(session, show)
