import uuid
from typing import Annotated

from fastapi import Depends, Path
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.service import get_first_or_error
from app.sources.models import Source


def get_user_source(
    session: SessionDep,
    current_user: CurrentUser,
    source_id: Annotated[uuid.UUID, Path()],
) -> Source:
    """Look up a source by its UUID id and verify user ownership."""
    statement = select(Source).where(Source.id == source_id)
    return get_first_or_error(session, statement, current_user.id, "Source")


UserSource = Annotated[Source, Depends(get_user_source)]
