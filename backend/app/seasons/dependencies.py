# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_owned_record, get_readable_record
from app.seasons.models import Season
from app.users.dependencies import OptionalUser


def require_owned_season(
    session: SessionDep,
    current_user: CurrentUser,
    season_id: Annotated[uuid.UUID, Path()],
) -> Season:
    """Get a season if it exists and belongs to the current user."""
    return get_owned_record(session, Season, season_id, current_user.id)


def require_readable_season(
    session: SessionDep,
    optional_user: OptionalUser,
    season_id: Annotated[uuid.UUID, Path()],
) -> Season:
    """Get a season if it exists and is readable by the current user."""
    return get_readable_record(session, Season, season_id, optional_user)


OwnedSeason = Annotated[Season, Depends(require_owned_season)]
ReadableSeason = Annotated[Season, Depends(require_readable_season)]
