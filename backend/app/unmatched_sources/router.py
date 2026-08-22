# TODO: Validate
from fastapi import APIRouter, Depends

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.schemas import Message
from app.unmatched_sources.dependencies import ExistingUnmatchedSource
from app.unmatched_sources.schemas import (
    UnmatchedSourceImport,
    UnmatchedSourceOutput,
)
from app.unmatched_sources.service import (
    import_unmatched_source,
    list_unmatched_sources,
)

unmatched_sources_router = APIRouter(
    prefix="/unmatched-sources",
    tags=["unmatched sources"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@unmatched_sources_router.get("")
def admin_get_unmatched_sources(
    session: SessionDep,
) -> list[UnmatchedSourceOutput]:
    return list_unmatched_sources(session)


# TODO: Validate
@unmatched_sources_router.post("/{unmatched_source_id}/import")  # noqa: FAST003 - Used by ExistingUnmatchedSource.
def admin_import_unmatched_source(
    session: SessionDep,
    unmatched_source: ExistingUnmatchedSource,
    import_input: UnmatchedSourceImport,
) -> Message:
    return import_unmatched_source(session, unmatched_source, import_input)


router = APIRouter()
router.include_router(unmatched_sources_router)
