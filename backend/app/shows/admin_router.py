# TODO: Validate


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
from app.canonical_media.read import canonical_list_response
from app.media.service import delete_record
from app.plugins.models import Plugin
from app.schemas import Message, ReadOptions
from app.service import list_response
from app.shows.dependencies import AdminCanonicalShow, ExistingShow
from app.shows.models import Show
from app.shows.schemas import (
    CanonicalShowOutput,
    CanonicalShowsPublic,
    ShowCreate,
    ShowImportUrlInput,
    ShowListPublic,
    ShowPublic,
    ShowsPublic,
    ShowTmdbUrlInput,
    ShowUpdate,
    TmdbEpisodeGroupOption,
    UnvalidatedShowOutput,
)
from app.shows.service import (
    _show_output,
    canonicalize_show,
    force_update_show,
    import_non_canonical_show_from_url,
    list_tmdb_episode_groups,
    list_unvalidated_shows,
    relink_show,
    set_canonical_show,
    set_canonical_show_using_tmdb_url,
    unset_canonical_show,
    update_show_record,
    validate_show,
)
from app.sources.dependencies import ExistingSource
from app.sources.models import Source

"""Show router."""


canonical_shows_router = APIRouter(
    prefix="/shows/canonical",
    tags=["canonical-shows"],
)


shows_router = APIRouter(
    prefix="/shows",
    tags=["shows"],
    dependencies=[Depends(get_current_active_superuser)],
)


source_shows_router = APIRouter(
    prefix="/sources/{source_id}",
    tags=["shows"],
    dependencies=[Depends(get_current_active_superuser)],
)


SHOW_EXTRA_COLUMNS: dict[str, Any] = {
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


# TODO: Validate
@source_shows_router.post("/shows")
def create_show(
    session: SessionDep,
    source: ExistingSource,
    show_input: ShowCreate,
) -> ShowPublic:
    return _show_output(show_input.create(session, Show, source))


# TODO: Validate
@shows_router.get("")
def get_shows(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ShowsPublic:
    """Get `Show`s."""
    return list_response(
        session=session,
        base=Show.select_with_plugin_eager(),
        response_model=ShowsPublic,
        schema=ShowListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=SHOW_EXTRA_COLUMNS,
    )


# TODO: Validate
@shows_router.get(
    "/unvalidated",
)
def admin_get_unvalidated_shows(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[UnvalidatedShowOutput]:
    """Get every `Show` whose canonical shows no `User` has validated."""
    return list_unvalidated_shows(session, limit)


# TODO: Validate
@shows_router.get(
    "/{show_id}",
)
def get_show(show: ExistingShow) -> ShowPublic:
    return _show_output(show)


# TODO: Validate
@shows_router.get(
    "/{show_id}/non-canonical",  # noqa: FAST003 - Used by ExistingShow.
)
def get_non_canonical_shows(show: ExistingShow) -> list[ShowListPublic]:
    return [
        ShowListPublic.model_validate(link.show) for link in show.non_canonical_shows
    ]


# TODO: Validate
@shows_router.patch(
    "/{show_id}",
)
def update_show(
    session: SessionDep,
    show: ExistingShow,
    show_input: ShowUpdate,
) -> ShowPublic:
    """Update a `Show`."""
    return update_show_record(session, show, show_input)


# TODO: Validate
@shows_router.put(
    "/{show_id}/canonical/{canonical_show_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_show_to_canonical(
    session: SessionDep,
    show: ExistingShow,
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
)
def admin_link_show_by_tmdb_url(
    session: SessionDep,
    show: ExistingShow,
    url_input: ShowTmdbUrlInput,
) -> ShowPublic:
    return _show_output(set_canonical_show_using_tmdb_url(session, show, url_input.url))


# TODO: Validate
@shows_router.post(
    "/{show_id}/non-canonical-by-url",  # noqa: FAST003 - Used by the dependencies.
)
def admin_import_non_canonical_show(
    session: SessionDep,
    show: ExistingShow,
    url_input: ShowImportUrlInput,
) -> ShowPublic:
    return _show_output(
        import_non_canonical_show_from_url(session, show, url_input.url),
    )


# TODO: Validate
@shows_router.delete(
    "/{show_id}/canonical/{canonical_show_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_unlink_show_from_canonical(
    session: SessionDep,
    show: ExistingShow,
    canonical_show: AdminCanonicalShow,
) -> ShowPublic:
    """Take one canonical show off what a `Show` stands for."""
    return _show_output(unset_canonical_show(session, show, canonical_show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/canonicalize",  # noqa: FAST003 - Used by ExistingShow.
)
def admin_canonicalize_show(session: SessionDep, show: ExistingShow) -> ShowPublic:
    return _show_output(canonicalize_show(session, show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/validate",  # noqa: FAST003 - Used by ExistingShow.
)
def admin_validate_show(session: SessionDep, show: ExistingShow) -> ShowPublic:
    """Settle the canonical shows a `Show` stands for as the right ones."""
    return _show_output(validate_show(session, show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/relink",  # noqa: FAST003 - Used by ExistingShow.
)
def admin_relink_show_episodes(
    session: SessionDep,
    show: ExistingShow,
) -> ShowPublic:
    """Work out every unsettled episode link on a `Show` again from scratch."""
    return _show_output(relink_show(session, show))


# TODO: Validate
@shows_router.post(
    "/{show_id}/force-update",  # noqa: FAST003 - Used by ExistingShow.
)
def admin_force_update_show(session: SessionDep, show: ExistingShow) -> ShowPublic:
    return _show_output(force_update_show(session, show))


# TODO: Validate
@shows_router.get(
    "/{show_id}/tmdb-episode-groups",  # noqa: FAST003 - Used by ExistingShow.
)
def get_show_tmdb_episode_groups(
    session: SessionDep,
    show: ExistingShow,
) -> list[TmdbEpisodeGroupOption]:
    """Get the episode orders TMDB holds for a `Show`, for one to be chosen."""
    return list_tmdb_episode_groups(session, show)


# TODO: Validate
@shows_router.delete(
    "/{show_id}",
)
def delete_show(session: SessionDep, show: ExistingShow) -> Message:
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


router = APIRouter()


router.include_router(canonical_shows_router)


router.include_router(shows_router)


router.include_router(source_shows_router)
