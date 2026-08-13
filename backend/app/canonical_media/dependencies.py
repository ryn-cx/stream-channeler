# TODO: Validate
"""Reach a canonical row by id, for admins only.

Canonical media is what every website's copy resolves to, so it is the same for
everybody and belongs to nobody. There is no owner to check and no visibility to
honour, which leaves one rule: only an admin may look at it at all.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_media.filters import is_canonical
from app.episodes.models import Episode
from app.seasons.models import Season
from app.shows.models import Show


# TODO: Validate
def get_canonical_show(
    session: SessionDep,
    _admin: SuperUser,
    canonical_show_id: uuid.UUID,
) -> Show:
    """Return the `Show` an id names."""
    canonical_show = session.exec(
        select(Show).where(is_canonical(Show), col(Show.id) == canonical_show_id),
    ).first()
    if canonical_show is None:
        raise HTTPException(status_code=404, detail="Canonical show not found")
    return canonical_show


# TODO: Validate
def get_canonical_season(
    session: SessionDep,
    _admin: SuperUser,
    canonical_season_id: uuid.UUID,
) -> Season:
    """Return the `Season` an id names.

    Looked up rather than asked of the session, since a season is named by the
    title above it and its own key and an id on its own is no such name.
    """
    canonical_season = session.exec(
        select(Season).where(
            is_canonical(Season),
            col(Season.id) == canonical_season_id,
        ),
    ).first()
    if canonical_season is None:
        raise HTTPException(status_code=404, detail="Canonical season not found")
    return canonical_season


# TODO: Validate
def get_canonical_episode(
    session: SessionDep,
    _admin: SuperUser,
    canonical_episode_id: uuid.UUID,
) -> Episode:
    """Return the `Episode` an id names.

    Looked up rather than asked of the session, since an episode is named by the
    season above it and its own key and an id on its own is no such name.
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


AdminCanonicalShow = Annotated[Show, Depends(get_canonical_show)]
AdminCanonicalSeason = Annotated[Season, Depends(get_canonical_season)]
AdminCanonicalEpisode = Annotated[Episode, Depends(get_canonical_episode)]
