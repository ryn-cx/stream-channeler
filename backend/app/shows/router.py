# TODO: Validate
"""Show router."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.media.tmdb_fallback import fill_shows
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.shows.dependencies import EditableShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowCreate,
    ShowListPublic,
    ShowPublic,
    ShowsPublic,
    ShowUpdate,
)
from app.shows.service import relink_children
from app.sources.dependencies import EditableSource, ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_shows_router = APIRouter(prefix="/plugins/{plugin_id}", tags=["shows"])
source_shows_router = APIRouter(prefix="/sources/{source_id}", tags=["shows"])
shows_router = APIRouter(prefix="/shows", tags=["shows"])

SHOW_EXTRA_COLUMNS: dict[str, Any] = {
    "username": User.username,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


def _show_output(session: SessionDep, show: Show) -> ShowPublic:
    """Return a `Show` with whatever its website left out taken from TMDB."""
    return fill_shows(session, [ShowPublic.model_validate(show)])[0]


@source_shows_router.post("/shows")
def create_show(
    session: SessionDep,
    source: EditableSource,
    show_input: ShowCreate,
) -> ShowPublic:
    """Create a `Show` if the `Source` is editable by the `User`."""
    return _show_output(session, show_input.create(session, Show, source))


@shows_router.get("")
def get_shows(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> ShowsPublic:
    """Get `Show`s."""
    shows = media_scoped_list_response(
        session=session,
        base=Show.select_with_user_eager(),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        read_options=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )
    fill_shows(session, shows.data)
    return shows


@source_shows_router.get("/shows")
def get_source_shows(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get all of the `Show`s for a `Source` if it is readable by the `User`."""
    shows = list_response(
        session=session,
        base=Show.select_with_user_eager().where(Show.source_id == source.id),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )
    fill_shows(session, shows.data)
    return shows


@plugin_shows_router.get("/shows")
def get_plugin_shows(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get all of the `Show`s for a `Plugin` if it is readable by the `User`."""
    shows = list_response(
        session=session,
        base=Show.select_with_user_eager().where(Source.plugin_id == plugin.id),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )
    fill_shows(session, shows.data)
    return shows


@shows_router.get("/{show_id}")  # noqa: FAST003 - Used by ReadableShow.
def get_show(session: SessionDep, show: ReadableShow) -> ShowPublic:
    """Get a `Show` if it's readable by the `User`."""
    return _show_output(session, show)


@shows_router.patch("/{show_id}")  # noqa: FAST003 - Used by EditableShow.
def update_show(
    session: SessionDep,
    show: EditableShow,
    show_input: ShowUpdate,
) -> ShowPublic:
    """Update and return a `Show` if it's editable by the `User`.

    A new `tmdb_id` repoints every `Season` and `Episode` at TMDB so their
    `tmdb_id` and `episode_identifier` follow the one the `User` chose.
    """
    previous_tmdb_id = show.tmdb_id
    show = show_input.update(session, show)
    if show.tmdb_id != previous_tmdb_id:
        relink_children(session, show)
    return _show_output(session, show)


@shows_router.delete("/{show_id}")  # noqa: FAST003 - Used by EditableShow.
def delete_show(session: SessionDep, show: EditableShow) -> Message:
    """Delete a `Show` if it's editable by the `User`."""
    return delete_record(session, show)


router = APIRouter()
router.include_router(shows_router)
router.include_router(source_shows_router)
router.include_router(plugin_shows_router)
