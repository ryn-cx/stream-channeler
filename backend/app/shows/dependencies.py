# TODO: Validate
"""Show dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_media.filters import is_canonical
from app.media.service import editable_record, readable_record
from app.shows.models import Show

ReadableShow = Annotated[Show, Depends(readable_record(Show, "show_id"))]
EditableShow = Annotated[Show, Depends(editable_record(Show, "show_id"))]


# TODO: Validate
def get_canonical_show(
    session: SessionDep,
    _admin: SuperUser,
    canonical_show_id: uuid.UUID,
) -> Show:
    """Return the `Show` an id names.

    A title is what every website's copy of it resolves to, so it is the same for
    everybody and belongs to nobody. There is no owner to check and no visibility
    to honour, which leaves one rule: only an admin may look at it at all.
    """
    canonical_show = session.exec(
        select(Show).where(is_canonical(Show), col(Show.id) == canonical_show_id),
    ).first()
    if canonical_show is None:
        raise HTTPException(status_code=404, detail="Canonical show not found")
    return canonical_show


AdminCanonicalShow = Annotated[Show, Depends(get_canonical_show)]
