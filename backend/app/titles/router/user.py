# TODO: Validate


from fastapi import APIRouter

from app.titles.dependencies import AdminTmdbTitle
from app.titles.schemas import TmdbTitleOutput

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


router = APIRouter()


router.include_router(titles_router)
router.include_router(tmdb_titles_router)
