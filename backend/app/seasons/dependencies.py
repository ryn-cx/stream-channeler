import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_first_or_error
from app.seasons.models import Season


def get_user_season(
    session: SessionDep,
    current_user: CurrentUser,
    season_id: Annotated[uuid.UUID, Path()],
) -> Season:
    """Look up a season by its UUID id and verify user ownership."""
    statement = select(Season).where(Season.id == season_id)
    return get_first_or_error(session, statement, current_user.id, "Season")


UserSeason = Annotated[Season, Depends(get_user_season)]
