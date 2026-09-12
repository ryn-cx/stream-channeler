# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import CurrentUser, SessionDep
from app.constants import SERVER_SIDE_THRESHOLD_MAXIMUM
from app.titles.dependencies import AdminTmdbTitle
from app.titles.schemas import (
    TitlesBrowsePublic,
    TmdbTitleOutput,
)
from app.titles.service.browse import browse_plugin_titles

"""Title router."""


tmdb_titles_router = APIRouter(
    prefix="/titles/tmdb",
    tags=["tmdb-titles"],
)


# TODO: Validate
@tmdb_titles_router.get("/{tmdb_title_id}")  # noqa: FAST003 - Used by AdminTmdbTitle.
def get_tmdb_title_by_id(
    tmdb_title: AdminTmdbTitle,
) -> TmdbTitleOutput:
    """Get a `Title`."""
    return TmdbTitleOutput.model_validate(tmdb_title)


titles_router = APIRouter(prefix="/titles", tags=["titles"])


# TODO: Validate
@titles_router.get("/browse")
def browse_titles(
    session: SessionDep,
    _current_user: CurrentUser,
    plugin_key: str,
    search: str | None = None,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[
        int,
        Query(ge=1, le=SERVER_SIDE_THRESHOLD_MAXIMUM),
    ] = 24,
) -> TitlesBrowsePublic:
    return browse_plugin_titles(session, plugin_key, search, offset, limit)


router = APIRouter()


router.include_router(titles_router)
router.include_router(tmdb_titles_router)
