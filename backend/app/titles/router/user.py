# TODO: Validate


from fastapi import APIRouter

from app.titles.dependencies import AdminCanonicalTitle
from app.titles.schemas import (
    CanonicalTitleOutput,
)

"""Title router."""


canonical_titles_router = APIRouter(
    prefix="/titles/canonical",
    tags=["canonical-titles"],
)


# TODO: Validate
@canonical_titles_router.get("/{canonical_title_id}")  # noqa: FAST003 - Used by AdminCanonicalTitle.
def get_canonical_title_by_id(
    canonical_title: AdminCanonicalTitle,
) -> CanonicalTitleOutput:
    """Get a `Title`."""
    return CanonicalTitleOutput.model_validate(canonical_title)


router = APIRouter()


router.include_router(canonical_titles_router)
