# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path

from app.auth.dependencies import SessionDep
from app.unmatched_sources.models import UnmatchedSource


# TODO: Validate
def existing_unmatched_source(
    session: SessionDep,
    record_id: Annotated[uuid.UUID, Path(alias="unmatched_source_id")],
) -> UnmatchedSource:
    unmatched_source = session.get(UnmatchedSource, record_id)
    if unmatched_source is None:
        raise HTTPException(status_code=404, detail="UnmatchedSource not found")
    return unmatched_source


ExistingUnmatchedSource = Annotated[
    UnmatchedSource,
    Depends(existing_unmatched_source),
]
