# TODO: Validate
"""Show router."""

from typing import Annotated, Any

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.issue_reports.service import list_show_issue_reports
from app.media.canonical_metadata import (
    canonical_show_of,
    fill_shows,
    tmdb_show_url,
)
from app.media.identifiers import TMDB_PLUGIN_KEY
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.plugins.dependencies import ReadablePlugin
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.shows.dependencies import EditableShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    ShowCreate,
    ShowInformationOutput,
    ShowInformationSide,
    ShowListPublic,
    ShowPublic,
    ShowsPublic,
    ShowUpdate,
)
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


# TODO: Validate
def _show_output(session: SessionDep, show: Show) -> ShowPublic:
    """Return a `Show` with whatever its website left out taken from TMDB."""
    return fill_shows(session, [ShowPublic.model_validate(show)])[0]


# TODO: Validate
@source_shows_router.post("/shows")
def create_show(
    session: SessionDep,
    source: EditableSource,
    show_input: ShowCreate,
) -> ShowPublic:
    """Create a `Show` if the `Source` is editable by the `User`."""
    return _show_output(session, show_input.create(session, Show, source))


# TODO: Validate
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


# TODO: Validate
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


# TODO: Validate
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


# TODO: Validate
def _information_side(label: str, show: Show, url: str | None) -> ShowInformationSide:
    return ShowInformationSide(
        label=label,
        name=show.name,
        media_type=show.media_type,
        description=show.description,
        image_url=show.image_url,
        url=url,
        key=show.key,
    )


# TODO: Validate
@shows_router.get("/{show_id}/information")  # noqa: FAST003 - Used by ReadableShow.
def get_show_information(
    session: SessionDep,
    show: ReadableShow,
    current_user: OptionalUser,
) -> ShowInformationOutput:
    """Return what the website and TMDB each say about a `Show`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    source = show.source

    counterpart = canonical_show_of(session, show.canonical_show_id)
    tmdb: ShowInformationSide | None = None
    if counterpart:
        tmdb = _information_side(
            TMDB_PLUGIN_KEY,
            counterpart,
            tmdb_show_url(counterpart.key),
        )

    editable = current_user is not None and (
        current_user.is_superuser or current_user.id == show.owner_id(session)
    )

    return ShowInformationOutput(
        show_id=show.id,
        canonical_show_locked=show.canonical_show_locked,
        editable=editable,
        issue_reports=list_show_issue_reports(session, show.id),
        source=_information_side(
            source.name or source.plugin.name or source.plugin.key,
            show,
            show.url,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
@shows_router.get("/{show_id}")  # noqa: FAST003 - Used by ReadableShow.
def get_show(session: SessionDep, show: ReadableShow) -> ShowPublic:
    """Get a `Show` if it's readable by the `User`."""
    return _show_output(session, show)


# TODO: Validate
@shows_router.patch("/{show_id}")  # noqa: FAST003 - Used by EditableShow.
def update_show(
    session: SessionDep,
    show: EditableShow,
    show_input: ShowUpdate,
) -> ShowPublic:
    """Update and return a `Show` if it's editable by the `User`.

    Which title this is a copy of is not something an update writes: it is the
    linker's to work out during an import, or a `User`'s to settle through the
    TMDB matching screens, so there is nothing to repoint here.
    """
    return _show_output(session, show_input.update(session, show))


# TODO: Validate
@shows_router.delete("/{show_id}")  # noqa: FAST003 - Used by EditableShow.
def delete_show(session: SessionDep, show: EditableShow) -> Message:
    """Delete a `Show` if it's editable by the `User`."""
    return delete_record(session, show)


router = APIRouter()
router.include_router(shows_router)
router.include_router(source_shows_router)
router.include_router(plugin_shows_router)
