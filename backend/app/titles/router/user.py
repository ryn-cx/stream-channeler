# TODO: Validate


from fastapi import APIRouter

from app.titles.dependencies import ExistingTmdbTitle
from app.titles.schemas import TmdbTitleOutput

"""Title router."""


tmdb_titles_router = APIRouter(
    prefix="/titles/tmdb",
    tags=["tmdb-titles"],
)


# TODO: Validate
@tmdb_titles_router.get("/{tmdb_title_id}")  # noqa: FAST003 - Used by ExistingTmdbTitle.
def get_tmdb_title_by_id(
    tmdb_title: ExistingTmdbTitle,
) -> TmdbTitleOutput:
    """Get a `Title`."""
    return TmdbTitleOutput.model_validate(tmdb_title)


titles_router = APIRouter(prefix="/titles", tags=["titles"])


router = APIRouter()


router.include_router(titles_router)
router.include_router(tmdb_titles_router)
