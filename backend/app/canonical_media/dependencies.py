# TODO: Validate
"""Reach a canonical row by id, for admins only.

Canonical media is what every website's copy resolves to, so it is the same for
everybody and belongs to nobody. There is no owner to check and no visibility to
honour, which leaves one rule: only an admin may look at it at all.
"""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException

from app.auth.dependencies import SessionDep, SuperUser
from app.episodes.models import CanonicalEpisode
from app.seasons.models import CanonicalSeason
from app.shows.models import CanonicalShow


# TODO: Validate
def get_canonical_show(
    session: SessionDep,
    _admin: SuperUser,
    canonical_show_id: uuid.UUID,
) -> CanonicalShow:
    """Return the `CanonicalShow` an id names."""
    canonical_show = session.get(CanonicalShow, canonical_show_id)
    if canonical_show is None:
        raise HTTPException(status_code=404, detail="Canonical show not found")
    return canonical_show


# TODO: Validate
def get_canonical_season(
    session: SessionDep,
    _admin: SuperUser,
    canonical_season_id: uuid.UUID,
) -> CanonicalSeason:
    """Return the `CanonicalSeason` an id names."""
    canonical_season = session.get(CanonicalSeason, canonical_season_id)
    if canonical_season is None:
        raise HTTPException(status_code=404, detail="Canonical season not found")
    return canonical_season


# TODO: Validate
def get_canonical_episode(
    session: SessionDep,
    _admin: SuperUser,
    canonical_episode_id: uuid.UUID,
) -> CanonicalEpisode:
    """Return the `CanonicalEpisode` an id names."""
    canonical_episode = session.get(CanonicalEpisode, canonical_episode_id)
    if canonical_episode is None:
        raise HTTPException(status_code=404, detail="Canonical episode not found")
    return canonical_episode


AdminCanonicalShow = Annotated[CanonicalShow, Depends(get_canonical_show)]
AdminCanonicalSeason = Annotated[CanonicalSeason, Depends(get_canonical_season)]
AdminCanonicalEpisode = Annotated[CanonicalEpisode, Depends(get_canonical_episode)]
