# TODO: Validate
"""Title dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_media.filters import is_canonical
from app.media.service.records import existing_record
from app.titles.models import Title

ExistingTitle = Annotated[Title, Depends(existing_record(Title, "title_id"))]


# TODO: Validate
def get_canonical_title(
    session: SessionDep,
    _admin: SuperUser,
    canonical_title_id: uuid.UUID,
) -> Title:
    """Return the `Title` an id names.

    A canonical title is what every website's row resolves to, so it is the same for
    everybody and belongs to nobody. There is no owner to check and no visibility
    to honour, which leaves one rule: only an admin may look at it at all.
    """
    canonical_title = session.exec(
        select(Title).where(is_canonical(Title), col(Title.id) == canonical_title_id),
    ).first()
    if canonical_title is None:
        raise HTTPException(status_code=404, detail="Canonical title not found")
    return canonical_title


AdminCanonicalTitle = Annotated[Title, Depends(get_canonical_title)]
