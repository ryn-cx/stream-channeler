"""Show router."""

from typing import Annotated

from fastapi import APIRouter, Query
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_list_response,
    media_owner_list_response,
)
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.shows.dependencies import EditableShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowCreate,
    ShowPublic,
    ShowsPublic,
    ShowUpdate,
)
from app.sources.dependencies import EditableSource, ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser

source_shows_router = APIRouter(prefix="/sources/{source_id}", tags=["shows"])
shows_router = APIRouter(prefix="/shows", tags=["shows"])


@source_shows_router.post("/shows", response_model=ShowPublic)
def create_show(
    session: SessionDep,
    source: EditableSource,
    show_input: ShowCreate,
) -> Show:
    """Create a `Show` if the `Source` is editable by the `User`."""
    return show_input.create(session, Show, source)


@shows_router.get("")
def get_shows(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> ShowsPublic:
    """Get all of the `Show`s readable by the `User`."""
    return media_owner_list_response(
        session=session,
        base=select(Show).join(Source).join(Plugin),
        response_model=ShowsPublic,
        schema=ShowPublic,
        read_options=read_options,
        current_user=current_user,
    )


@source_shows_router.get("/shows")
def get_source_shows(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get all of the `Show`s for a `Source` if it is readable by the `User`."""
    base = select(Show).where(Show.source_id == source.id)
    return media_list_response(
        session=session,
        base=base,
        response_model=ShowsPublic,
        schema=ShowPublic,
        params=read_options,
        current_user=current_user,
    )


@shows_router.get("/{show_id}", response_model=ShowPublic)  # noqa: FAST003 - Used by ReadableShow
def get_show(show: ReadableShow) -> Show:
    """Get a `Show` if it's readable by the `User`."""
    return show


@shows_router.patch("/{show_id}", response_model=ShowPublic)  # noqa: FAST003 - Used by EditableShow
def update_show(
    session: SessionDep,
    show: EditableShow,
    show_input: ShowUpdate,
) -> Show:
    """Update and return a `Show` if it's editable by the `User`."""
    return show_input.update(session, show)


@shows_router.delete("/{show_id}")  # noqa: FAST003 - Used by EditableShow
def delete_show(session: SessionDep, show: EditableShow) -> Message:
    """Delete a `Show` if it's editable by the `User`."""
    return delete_record(session, show)


router = APIRouter()
router.include_router(shows_router)
router.include_router(source_shows_router)
