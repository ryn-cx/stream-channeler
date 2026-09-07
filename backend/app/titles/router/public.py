# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.titles.dependencies import ExistingTitle
from app.titles.schemas import (
    TitleInformationOutput,
)
from app.titles.service.service import title_information
from app.users.dependencies import OptionalUser

"""Title router."""


titles_router = APIRouter(prefix="/titles", tags=["titles"])


# TODO: Validate
@titles_router.get("/{title_id}/information")  # noqa: FAST003 - Used by ExistingTitle.
def get_title_information(
    session: SessionDep,
    title: ExistingTitle,
    current_user: OptionalUser,
) -> TitleInformationOutput:
    """Return what the website and TMDB each say about a `Title`."""
    return title_information(session, title, current_user)


router = APIRouter()


router.include_router(titles_router)
