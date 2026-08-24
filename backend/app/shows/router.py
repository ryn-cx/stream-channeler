# TODO: Validate
"""Show router."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlmodel import select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.canonical_media.filters import is_canonical
from app.canonical_media.metadata import (
    canonical_show_of,
    tmdb_show_url,
)
from app.canonical_media.read import canonical_list_response
from app.issue_reports.service import list_show_issue_reports
from app.media.schemas import MediaReadOptions
from app.media.service import (
    delete_record,
    media_scoped_list_response,
)
from app.plugins.dependencies import ReadablePlugin
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.shows.dependencies import AdminCanonicalShow, EditableShow, ReadableShow
from app.shows.models import Show
from app.shows.schemas import (
    CanonicalShowOutput,
    CanonicalShowsPublic,
    ShowCreate,
    ShowImportUrlInput,
    ShowInformationOutput,
    ShowInformationSide,
    ShowListPublic,
    ShowPublic,
    ShowsPublic,
    ShowTmdbUrlInput,
    ShowUpdate,
    TmdbEpisodeGroupOption,
    UnvalidatedShowOutput,
)
from app.shows.service import (
    canonicalize_show,
    force_update_show,
    import_non_canonical_show_from_url,
    list_tmdb_episode_groups,
    list_unvalidated_shows,
    relink_show,
    set_canonical_show,
    set_canonical_show_using_tmdb_url,
    unset_canonical_show,
    update_show_extra,
    validate_show,
)
from app.sources.dependencies import EditableSource, ReadableSource
from app.sources.models import Source
from app.users.dependencies import OptionalUser
from app.users.models import User

plugin_shows_router = APIRouter(
    prefix="/plugins/{plugin_id}",
    tags=["shows"],
    dependencies=[Depends(get_current_active_superuser)],
)
source_shows_router = APIRouter(
    prefix="/sources/{source_id}",
    tags=["shows"],
    dependencies=[Depends(get_current_active_superuser)],
)
shows_router = APIRouter(prefix="/shows", tags=["shows"])
canonical_shows_router = APIRouter(
    prefix="/shows/canonical",
    tags=["canonical-shows"],
)

SHOW_EXTRA_COLUMNS: dict[str, Any] = {
    "username": User.username,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


# TODO: Validate
def _show_output(show: Show) -> ShowPublic:
    """Return a `Show` as the website that holds it stored it."""
    return ShowPublic.model_validate(show)


# TODO: Validate
@source_shows_router.post("/shows")
def create_show(
    session: SessionDep,
    source: EditableSource,
    show_input: ShowCreate,
) -> ShowPublic:
    """Create a `Show` if the `Source` is editable by the `User`."""
    return _show_output(show_input.create(session, Show, source))


# TODO: Validate
@shows_router.get("", dependencies=[Depends(get_current_active_superuser)])
def get_shows(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[MediaReadOptions, Query()],
) -> ShowsPublic:
    """Get `Show`s."""
    return media_scoped_list_response(
        session=session,
        base=Show.select_with_user_eager(),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        read_options=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )


# TODO: Validate
@source_shows_router.get("/shows")
def get_source_shows(
    session: SessionDep,
    source: ReadableSource,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get all of the `Show`s for a `Source` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Show.select_with_user_eager().where(Show.source_id == source.id),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )


# TODO: Validate
@plugin_shows_router.get("/shows")
def get_plugin_shows(
    session: SessionDep,
    plugin: ReadablePlugin,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get all of the `Show`s for a `Plugin` if it is readable by the `User`."""
    return list_response(
        session=session,
        base=Show.select_with_user_eager().where(Source.plugin_id == plugin.id),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )


# TODO: Validate
@shows_router.get(
    "/unvalidated",
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_get_unvalidated_shows(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[UnvalidatedShowOutput]:
    """Get every `Show` whose canonical shows no `User` has validated."""
    return list_unvalidated_shows(session, limit)


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

    counterpart = canonical_show_of(session, show)
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
        canonical_show_validated_at=show.canonical_show_validated_at,
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
@shows_router.get(
    "/{show_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def get_show(show: ReadableShow) -> ShowPublic:
    """Get a `Show` if it's readable by the `User`."""
    return _show_output(show)


# TODO: Validate
@shows_router.get(
    "/{show_id}/non-canonical",  # noqa: FAST003 - Used by ReadableShow.
    dependencies=[Depends(get_current_active_superuser)],
)
def get_non_canonical_shows(show: ReadableShow) -> list[ShowListPublic]:
    return [
        ShowListPublic.model_validate(link.show) for link in show.non_canonical_shows
    ]


# TODO: Validate
@shows_router.patch(
    "/{show_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def update_show(
    session: SessionDep,
    show: EditableShow,
    show_input: ShowUpdate,
) -> ShowPublic:
    """Update and return a `Show` if it's editable by the `User`.

    Which canonical show this stands for is not something an update writes: it is
    linker's to work out during an import, or a `User`'s to settle through the
    TMDB matching screens, so there is nothing to repoint here.

    `extra` goes through its own service rather than being written with the rest, since
    what a TMDB row keeps there is the episode order the title is read in and changing
    that means reading the title again and matching every non-canonical row of it
    afresh.
    """
    # Before the rest of the update, because what it does depends on the order
    # the title is read in now and the general write would already have replaced
    # it. The same value going down twice writes nothing the second time.
    if "extra" in show_input.model_fields_set:
        update_show_extra(session, show, show_input.extra)
    return _show_output(show_input.update(session, show))


# TODO: Validate
@shows_router.put(
    "/{show_id}/canonical/{canonical_show_id}",  # noqa: FAST003 - Used by the dependencies.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_link_show_to_canonical(
    session: SessionDep,
    show: EditableShow,
    canonical_show: AdminCanonicalShow,
) -> ShowPublic:
    """Add the canonical show an admin chose to what a `Show` stands for.

    Its own endpoint rather than part of the update, because the link is a row of
    its own and what it drags along - the episodes being read again against the
    title chosen - is not something a write of the show's own columns does.

    Added to whatever the row already stands for rather than put in its place,
    since one page holding two titles is a thing websites do. Taking one off is
    `admin_unlink_show_from_canonical`.
    """
    return _show_output(set_canonical_show(session, show, canonical_show))


# TODO: Validate
@shows_router.put(
    "/{show_id}/canonical-by-tmdb-url",  # noqa: FAST003 - Used by the dependencies.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_link_show_by_tmdb_url(
    session: SessionDep,
    show: EditableShow,
    url_input: ShowTmdbUrlInput,
) -> ShowPublic:
    return _show_output(set_canonical_show_using_tmdb_url(session, show, url_input.url))


# TODO: Validate
@shows_router.post(
    "/{show_id}/non-canonical-by-url",  # noqa: FAST003 - Used by the dependencies.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_import_non_canonical_show(
    session: SessionDep,
    show: EditableShow,
    url_input: ShowImportUrlInput,
) -> ShowPublic:
    return _show_output(
        import_non_canonical_show_from_url(session, show, url_input.url),
    )


# TODO: Validate
@shows_router.delete(
    "/{show_id}/canonical/{canonical_show_id}",  # noqa: FAST003 - Used by the dependencies.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_unlink_show_from_canonical(
    session: SessionDep,
    show: EditableShow,
    canonical_show: AdminCanonicalShow,
) -> ShowPublic:
    """Take one canonical show off what a `Show` stands for."""
    return _show_output(unset_canonical_show(session, show, canonical_show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/canonicalize",  # noqa: FAST003 - Used by EditableShow.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_canonicalize_show(session: SessionDep, show: EditableShow) -> ShowPublic:
    return _show_output(canonicalize_show(session, show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/validate",  # noqa: FAST003 - Used by EditableShow.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_validate_show(session: SessionDep, show: EditableShow) -> ShowPublic:
    """Settle the canonical shows a `Show` stands for as the right ones."""
    return _show_output(validate_show(session, show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/relink",  # noqa: FAST003 - Used by EditableShow.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_relink_show_episodes(
    session: SessionDep,
    show: EditableShow,
) -> ShowPublic:
    """Work out every unsettled episode link on a `Show` again from scratch."""
    return _show_output(relink_show(session, show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/force-update",  # noqa: FAST003 - Used by EditableShow.
    dependencies=[Depends(get_current_active_superuser)],
)
def admin_force_update_show(session: SessionDep, show: EditableShow) -> ShowPublic:
    return _show_output(force_update_show(session, show))


# TODO: Validate
@shows_router.get(
    "/{show_id}/tmdb-episode-groups",  # noqa: FAST003 - Used by ReadableShow.
    dependencies=[Depends(get_current_active_superuser)],
)
def get_show_tmdb_episode_groups(
    session: SessionDep,
    show: ReadableShow,
) -> list[TmdbEpisodeGroupOption]:
    """Get the episode orders TMDB holds for a `Show`, for one to be chosen."""
    return list_tmdb_episode_groups(session, show)


# TODO: Validate
@shows_router.delete(
    "/{show_id}",
    dependencies=[Depends(get_current_active_superuser)],
)
def delete_show(session: SessionDep, show: EditableShow) -> Message:
    """Delete a `Show` if it's editable by the `User`."""
    return delete_record(session, show)


# The admin-only mirror of the show endpoints. A non-canonical `Show` is one website's
# row and is served to whoever may see that website's media; a canonical `Show` is the
# show itself, which every row standing for it resolves to, and is served to admins
# alone.
# TODO: Validate
@canonical_shows_router.get("")
def get_canonical_shows(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalShowsPublic:
    """Get every `Show`."""
    return canonical_list_response(
        session=session,
        base=select(Show).where(is_canonical(Show)),
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
    """Get a `Show`."""
    return CanonicalShowOutput.model_validate(canonical_show)


router = APIRouter()
# Registered ahead of `shows_router` so "/shows/canonical" is read as the
# canonical collection rather than as a `Show` id that happens to be misspelt.
router.include_router(canonical_shows_router)
router.include_router(shows_router)
router.include_router(source_shows_router)
router.include_router(plugin_shows_router)
