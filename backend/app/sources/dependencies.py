# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_readable_resource, get_user_resource
from app.sources.models import Source
from app.users.dependencies import OptionalUser


def require_user_source(
    session: SessionDep,
    current_user: CurrentUser,
    source_id: Annotated[uuid.UUID, Path()],
) -> Source:
    return get_user_resource(session, Source, source_id, current_user.id)


UserSource = Annotated[Source, Depends(require_user_source)]


def require_readable_source(
    session: SessionDep,
    optional_user: OptionalUser,
    source_id: Annotated[uuid.UUID, Path()],
) -> Source:
    return get_readable_resource(session, Source, source_id, optional_user)


ReadableSource = Annotated[Source, Depends(require_readable_source)]
