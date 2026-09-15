# TODO: Validate
"""Episode dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep, SuperUser
from app.episodes.models import Episode
from app.media.service.records import existing_record
from app.tmdb_media.filters import is_not_linked

ExistingEpisode = Annotated[Episode, Depends(existing_record(Episode, "episode_id"))]


# TODO: Validate
def get_tmdb_episode(
    session: SessionDep,
    _admin: SuperUser,
    tmdb_episode_id: uuid.UUID,
) -> Episode:
    """Return the `Episode` an id names.

    Looked up rather than asked of the session, since an episode is named by the
    season above it and its own key and an id on its own is no such name.

    An episode is what every website's non-canonical row of it resolves to, so it is the
    same for everybody and belongs to nobody. There is no owner to check and no
    visibility to honour, which leaves one rule: only an admin may look at it at all.
    """
    tmdb_episode = session.exec(
        select(Episode).where(
            is_not_linked(Episode),
            col(Episode.id) == tmdb_episode_id,
        ),
    ).first()
    if tmdb_episode is None:
        raise HTTPException(status_code=404, detail="Canonical episode not found")
    return tmdb_episode


AdminTmdbEpisode = Annotated[Episode, Depends(get_tmdb_episode)]
