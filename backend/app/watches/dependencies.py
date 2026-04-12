import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_owned_record
from app.watches.models import Watch


def require_owned_watch(
    session: SessionDep,
    current_user: CurrentUser,
    watch_id: Annotated[uuid.UUID, Path()],
) -> Watch:
    return get_owned_record(session, Watch, watch_id, current_user.id)


OwnedWatch = Annotated[Watch, Depends(require_owned_watch)]
