# TODO: Validate


from fastapi import APIRouter

from app.shows.dependencies import AdminCanonicalShow
from app.shows.schemas import (
    CanonicalShowOutput,
)

"""Show router."""


canonical_shows_router = APIRouter(
    prefix="/shows/canonical",
    tags=["canonical-shows"],
)


# TODO: Validate
@canonical_shows_router.get("/{canonical_show_id}")  # noqa: FAST003 - Used by AdminCanonicalShow.
def get_canonical_show_by_id(
    canonical_show: AdminCanonicalShow,
) -> CanonicalShowOutput:
    """Get a `Show`."""
    return CanonicalShowOutput.model_validate(canonical_show)


router = APIRouter()


router.include_router(canonical_shows_router)
