import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_readable_resource, get_user_resource
from app.seasons.models import Season
from app.users.dependencies import OptionalUser


def require_user_season(
    session: SessionDep,
    current_user: CurrentUser,
    season_id: Annotated[uuid.UUID, Path()],
) -> Season:
    return get_user_resource(session, Season, season_id, current_user.id)


UserSeason = Annotated[Season, Depends(require_user_season)]


def require_readable_season(
    session: SessionDep,
    optional_user: OptionalUser,
    season_id: Annotated[uuid.UUID, Path()],
) -> Season:
    return get_readable_resource(session, Season, season_id, optional_user)


ReadableSeason = Annotated[Season, Depends(require_readable_season)]
