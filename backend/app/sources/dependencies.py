# TODO: Validate
"""Source dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path

from app.auth.dependencies import SessionDep
from app.media.service.records import existing_record
from app.sources.models import Source, UnmatchedSource

ExistingSource = Annotated[Source, Depends(existing_record(Source, "source_id"))]


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
