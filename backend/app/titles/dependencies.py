# TODO: Validate
"""Title dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep, SuperUser
from app.media.service.records import existing_record
from app.titles.models import Title
from app.tmdb_media.filters import is_not_linked

ExistingTitle = Annotated[Title, Depends(existing_record(Title, "title_id"))]


# TODO: Validate
def get_tmdb_title(
    session: SessionDep,
    _admin: SuperUser,
    tmdb_title_id: uuid.UUID,
) -> Title:
    """Return the `Title` an id names.

    A canonical title is what every website's row resolves to, so it is the same for
    everybody and belongs to nobody. There is no owner to check and no visibility
    to honour, which leaves one rule: only an admin may look at it at all.
    """
    tmdb_title = session.exec(
        select(Title).where(is_not_linked(Title), col(Title.id) == tmdb_title_id),
    ).first()
    if tmdb_title is None:
        raise HTTPException(status_code=404, detail="Canonical title not found")
    return tmdb_title


AdminTmdbTitle = Annotated[Title, Depends(get_tmdb_title)]
