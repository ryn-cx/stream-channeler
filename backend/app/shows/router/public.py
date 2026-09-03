# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.shows.dependencies import ExistingShow
from app.shows.schemas import (
    ShowInformationOutput,
)
from app.shows.service import show_information
from app.users.dependencies import OptionalUser

"""Show router."""


shows_router = APIRouter(prefix="/shows", tags=["shows"])


# TODO: Validate
@shows_router.get("/{show_id}/information")  # noqa: FAST003 - Used by ExistingShow.
def get_show_information(
    session: SessionDep,
    show: ExistingShow,
    current_user: OptionalUser,
) -> ShowInformationOutput:
    """Return what the website and TMDB each say about a `Show`."""
    return show_information(session, show, current_user)


router = APIRouter()


router.include_router(shows_router)
