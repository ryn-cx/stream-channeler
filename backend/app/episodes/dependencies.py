# TODO: Validate
"""Episode dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep
from app.episodes.models import Episode
from app.media.service.records import existing_record
from app.tmdb_media.filters import is_not_linked

ExistingEpisode = Annotated[Episode, Depends(existing_record(Episode, "episode_id"))]


# TODO: Validate
def get_tmdb_episode(
    session: SessionDep,
    tmdb_episode_id: uuid.UUID,
) -> Episode:
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
