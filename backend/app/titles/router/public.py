# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.seasons.schemas import SeasonWithEpisodeCountOutput
from app.seasons.service.listing import title_seasons
from app.titles.dependencies import ExistingTitle
from app.titles.schemas import (
    TitleInformationOutput,
    TitleListPublic,
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


# TODO: Validate
@titles_router.get("/{title_id}/seasons")  # noqa: FAST003 - Used by ExistingTitle.
def get_title_seasons(
    session: SessionDep,
    title: ExistingTitle,
) -> list[SeasonWithEpisodeCountOutput]:
    """Return every `Season` a `Title` holds."""
    return title_seasons(session, title)


# TODO: Validate
@titles_router.get(
    "/{title_id}/linked",  # noqa: FAST003 - Used by ExistingTitle.
)
def get_linked_titles(title: ExistingTitle) -> list[TitleListPublic]:
    return [
        TitleListPublic.model_validate(link.linked_title)
        for link in title.linked_title_links
    ]


router = APIRouter()


router.include_router(titles_router)
