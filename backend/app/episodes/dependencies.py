# TODO: Validate
"""Episode dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_media.filters import is_canonical
from app.episodes.models import Episode
from app.media.service import editable_record, existing_record, readable_record

ReadableEpisode = Annotated[Episode, Depends(readable_record(Episode, "episode_id"))]
EditableEpisode = Annotated[Episode, Depends(editable_record(Episode, "episode_id"))]
ExistingEpisode = Annotated[Episode, Depends(existing_record(Episode, "episode_id"))]


# TODO: Validate
def get_canonical_episode(
    session: SessionDep,
    _admin: SuperUser,
    canonical_episode_id: uuid.UUID,
) -> Episode:
    """Return the `Episode` an id names.

    Looked up rather than asked of the session, since an episode is named by the
    season above it and its own key and an id on its own is no such name.

    An episode is what every website's copy of it resolves to, so it is the same
    for everybody and belongs to nobody. There is no owner to check and no
    visibility to honour, which leaves one rule: only an admin may look at it at
    all.
    """
    canonical_episode = session.exec(
        select(Episode).where(
            is_canonical(Episode),
            col(Episode.id) == canonical_episode_id,
        ),
    ).first()
    if canonical_episode is None:
        raise HTTPException(status_code=404, detail="Canonical episode not found")
    return canonical_episode


AdminCanonicalEpisode = Annotated[Episode, Depends(get_canonical_episode)]
