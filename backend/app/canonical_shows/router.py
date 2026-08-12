# TODO: Validate
"""Canonical show router.

The admin-only mirror of the show router. A `Show` is one website's copy of a
title and is served to whoever may see that website's media; a `CanonicalShow`
is the title itself, which every copy of it resolves to, and is served to
admins alone.
"""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlmodel import select

from app.auth.dependencies import SessionDep, SuperUser
from app.canonical_media.dependencies import AdminCanonicalShow
from app.canonical_media.read import canonical_list_response
from app.canonical_shows.models import CanonicalShow
from app.canonical_shows.schemas import CanonicalShowOutput, CanonicalShowsPublic
from app.schemas import ReadOptions

canonical_shows_router = APIRouter(
    prefix="/canonical-shows",
    tags=["canonical-shows"],
)


# TODO: Validate
@canonical_shows_router.get("")
def get_canonical_shows(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalShowsPublic:
    """Get every `CanonicalShow`."""
    return canonical_list_response(
        session=session,
        base=select(CanonicalShow),
        response_model=CanonicalShowsPublic,
        schema=CanonicalShowOutput,
        read_options=read_options,
        current_user=current_user,
    )


# TODO: Validate
@canonical_shows_router.get("/{canonical_show_id}")  # noqa: FAST003 - Used by AdminCanonicalShow.
def get_canonical_show_by_id(
    canonical_show: AdminCanonicalShow,
) -> CanonicalShowOutput:
    """Get a `CanonicalShow`."""
    return CanonicalShowOutput.model_validate(canonical_show)


router = APIRouter()
router.include_router(canonical_shows_router)
