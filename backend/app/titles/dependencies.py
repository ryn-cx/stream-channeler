# TODO: Validate
"""Title dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path
from sqlmodel import col, select

from app.auth.dependencies import SessionDep
from app.media.service.records import existing_record
from app.plugins.identifiers import TMDB_SOURCE_KEY
from app.sources.models import Source
from app.titles.models import Title, UnmatchedTitle
from app.tmdb_media.filters import is_not_linked

ExistingTitle = Annotated[Title, Depends(existing_record(Title, "title_id"))]


# TODO: Validate
def existing_tmdb_title(
    session: SessionDep,
    tmdb_title_id: uuid.UUID,
) -> Title:
    """Return the `Title` an id names."""
    tmdb_title = session.exec(
        select(Title)
        .join(Source)
        .where(
            is_not_linked(Title),
            Source.key == TMDB_SOURCE_KEY,
            col(Title.id) == tmdb_title_id,
        ),
    ).first()
    if tmdb_title is None:
        raise HTTPException(status_code=404, detail="Canonical title not found")
    return tmdb_title


ExistingTmdbTitle = Annotated[Title, Depends(existing_tmdb_title)]


# TODO: Validate
def existing_unmatched_title(
    session: SessionDep,
    record_id: Annotated[uuid.UUID, Path(alias="unmatched_title_id")],
) -> UnmatchedTitle:
    unmatched_title = session.get(UnmatchedTitle, record_id)
    if unmatched_title is None:
        raise HTTPException(status_code=404, detail="UnmatchedTitle not found")
    return unmatched_title


ExistingUnmatchedTitle = Annotated[
    UnmatchedTitle,
    Depends(existing_unmatched_title),
]
