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
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.service.responses import list_response
from app.sources.models import Source
from app.titles.dependencies import AdminCanonicalTitle, ExistingTitle
from app.titles.models import Title
from app.titles.schemas import (
    CanonicalTitleOutput,
    CanonicalTitlesPublic,
    TitleImportUrlInput,
    TitleListPublic,
    TitlePublic,
    TitlesPublic,
    TitleTmdbUrlInput,
    TitleUpdate,
    TmdbEpisodeGroupOption,
    UnvalidatedTitleOutput,
)
from app.titles.service.canonical import (
    canonicalize_title,
    import_non_canonical_title_from_url,
    set_canonical_title,
    set_canonical_title_using_tmdb_url,
    unset_canonical_title,
)
from app.titles.service.extra import force_update_title, list_tmdb_episode_groups
from app.titles.service.information import _title_output, update_title_record
from app.titles.service.relinking import relink_title
from app.titles.service.validation import list_unvalidated_titles, validate_title

"""Title router."""


canonical_titles_router = APIRouter(
    prefix="/titles/canonical",
    tags=["canonical-titles"],
)


titles_router = APIRouter(
    prefix="/titles",
    tags=["titles"],
    dependencies=[Depends(get_current_active_superuser)],
)


TITLE_EXTRA_COLUMNS: dict[str, Any] = {
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.key,
}


# TODO: Validate
@titles_router.get("")
def get_titles(
    session: SessionDep,
    current_user: CurrentUser,
    read_options: Annotated[ReadOptions, Query()],
) -> TitlesPublic:
    """Get `Title`s."""
    return list_response(
        session=session,
        base=Title.select_with_plugin_eager(),
        response_model=TitlesPublic,
        schema=TitleListPublic,
        params=read_options,
        current_user=current_user,
        extra_columns=TITLE_EXTRA_COLUMNS,
    )


# TODO: Validate
@titles_router.get(
    "/unvalidated",
)
def admin_get_unvalidated_titles(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[UnvalidatedTitleOutput]:
    """Get every `Title` whose canonical titles no `User` has validated."""
    return list_unvalidated_titles(session, limit)


# TODO: Validate
@titles_router.get(
    "/{title_id}",
)
def get_title(title: ExistingTitle) -> TitlePublic:
    return _title_output(title)


# TODO: Validate
@titles_router.get(
    "/{title_id}/non-canonical",  # noqa: FAST003 - Used by ExistingTitle.
)
def get_non_canonical_titles(title: ExistingTitle) -> list[TitleListPublic]:
    return [
        TitleListPublic.model_validate(link.non_canonical_title)
        for link in title.non_canonical_title_links
    ]


# TODO: Validate
@titles_router.patch(
    "/{title_id}",
)
def update_title(
    session: SessionDep,
    title: ExistingTitle,
    title_input: TitleUpdate,
) -> TitlePublic:
    """Update a `Title`."""
    return update_title_record(session, title, title_input)


# TODO: Validate
@titles_router.put(
    "/{title_id}/canonical/{canonical_title_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_title_to_canonical(
    session: SessionDep,
    title: ExistingTitle,
    canonical_title: AdminCanonicalTitle,
) -> TitlePublic:
    """Add the canonical title an admin chose to what a `Title` stands for.

    Its own endpoint rather than part of the update, because the link is a row of
    its own and what it drags along - the episodes being read again against the
    title chosen - is not something a write of the title's own columns does.

    Added to whatever the row already stands for rather than put in its place,
    since one page holding two titles is a thing websites do. Taking one off is
    `admin_unlink_title_from_canonical`.
    """
    return _title_output(set_canonical_title(session, title, canonical_title))


# TODO: Validate
@titles_router.put(
    "/{title_id}/canonical-by-tmdb-url",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_title_by_tmdb_url(
    session: SessionDep,
    title: ExistingTitle,
    url_input: TitleTmdbUrlInput,
) -> TitlePublic:
    return _title_output(
        set_canonical_title_using_tmdb_url(session, title, url_input.url),
    )


# TODO: Validate
@titles_router.post(
    "/{title_id}/non-canonical-by-url",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_non_canonical_title_by_url(
    session: SessionDep,
    title: ExistingTitle,
    url_input: TitleImportUrlInput,
) -> TitlePublic:
    return _title_output(
        import_non_canonical_title_from_url(session, title, url_input.url),
    )


# TODO: Validate
@titles_router.delete(
    "/{title_id}/canonical/{canonical_title_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_unlink_title_from_canonical(
    session: SessionDep,
    title: ExistingTitle,
    canonical_title: AdminCanonicalTitle,
) -> TitlePublic:
    """Take one canonical title off what a `Title` stands for."""
    return _title_output(unset_canonical_title(session, title, canonical_title))


# TODO: Validate
@titles_router.post(
    "/{title_id}/canonicalize",  # noqa: FAST003 - Used by ExistingTitle.
)
def admin_canonicalize_title(session: SessionDep, title: ExistingTitle) -> TitlePublic:
    return _title_output(canonicalize_title(session, title))


# TODO: Validate
@titles_router.post(
    "/{title_id}/validate",  # noqa: FAST003 - Used by ExistingTitle.
)
def admin_validate_title(session: SessionDep, title: ExistingTitle) -> TitlePublic:
    """Settle the canonical titles a `Title` stands for as the right ones."""
    return _title_output(validate_title(session, title))


# TODO: Validate
@titles_router.post(
    "/{title_id}/relink",  # noqa: FAST003 - Used by ExistingTitle.
)
def admin_relink_title_episodes(
    session: SessionDep,
    title: ExistingTitle,
) -> TitlePublic:
    """Work out every unsettled episode link on a `Title` again from scratch."""
    return _title_output(relink_title(session, title))


# TODO: Validate
@titles_router.post(
    "/{title_id}/force-update",  # noqa: FAST003 - Used by ExistingTitle.
)
def admin_force_update_title(session: SessionDep, title: ExistingTitle) -> TitlePublic:
    return _title_output(force_update_title(session, title))


# TODO: Validate
@titles_router.get(
    "/{title_id}/tmdb-episode-groups",  # noqa: FAST003 - Used by ExistingTitle.
)
def get_title_tmdb_episode_groups(
    session: SessionDep,
    title: ExistingTitle,
) -> list[TmdbEpisodeGroupOption]:
    """Get the episode orders TMDB holds for a `Title`, for one to be chosen."""
    return list_tmdb_episode_groups(session, title)


# The admin-only mirror of the title endpoints. A non-canonical `Title` is one website's
# row and is served to whoever may see that website's media; a canonical `Title` is the
# title itself, which every row standing for it resolves to, and is served to admins
# alone.
# TODO: Validate
@canonical_titles_router.get("")
def get_canonical_titles(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> CanonicalTitlesPublic:
    """Get every `Title`."""
    return canonical_list_response(
        session=session,
        base=select(Title).where(is_canonical(Title)),
        response_model=CanonicalTitlesPublic,
        schema=CanonicalTitleOutput,
        read_options=read_options,
        current_user=current_user,
    )


router = APIRouter()


router.include_router(canonical_titles_router)


router.include_router(titles_router)
