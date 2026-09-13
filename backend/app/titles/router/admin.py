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
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.service.responses import list_response
from app.sources.models import Source
from app.titles.dependencies import AdminTmdbTitle, ExistingTitle
from app.titles.models import Title
from app.titles.schemas import (
    MissingSourceTitleOutput,
    TitleImportUrlInput,
    TitleListPublic,
    TitlePublic,
    TitlesPublic,
    TitleTmdbUrlInput,
    TitleUpdate,
    TmdbEpisodeGroupOption,
    TmdbTitleOutput,
    TmdbTitlesPublic,
    UnvalidatedTitleOutput,
)
from app.titles.service.linking import (
    old_import_linked_title_from_url,
    old_link_title_to_tmdb_title,
    old_link_title_to_tmdb_title_from_url,
    old_make_title_unlinked,
    old_relink_title,
    old_unlink_title_from_tmdb_title,
)
from app.titles.service.service import (
    _title_output,
    force_update_title,
    list_titles_missing_sources,
    list_tmdb_episode_groups,
    list_unvalidated_titles,
    update_title_record,
    validate_title,
)
from app.tmdb_media.filters import is_not_linked
from app.tmdb_media.read import tmdb_list_response

"""Title router."""


tmdb_titles_router = APIRouter(
    prefix="/titles/tmdb",
    tags=["tmdb-titles"],
)


titles_router = APIRouter(
    prefix="/titles",
    tags=["titles"],
    dependencies=[Depends(get_current_active_superuser)],
)


TITLE_EXTRA_COLUMNS: dict[str, Any] = {
    "source_key": Source.key,
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
    "/missing-sources",
)
def admin_get_titles_missing_sources(
    session: SessionDep,
    limit: Annotated[int, Query(ge=1, le=1000)] = 200,
) -> list[MissingSourceTitleOutput]:
    """Get every canonical TMDB title that no website's row stands for."""
    return list_titles_missing_sources(session, limit)


# TODO: Validate
@titles_router.get(
    "/{title_id}",
)
def get_title(title: ExistingTitle) -> TitlePublic:
    return _title_output(title)


# TODO: Validate
@titles_router.get(
    "/{title_id}/linked",  # noqa: FAST003 - Used by ExistingTitle.
)
def get_linked_titles(title: ExistingTitle) -> list[TitleListPublic]:
    return [
        TitleListPublic.model_validate(link.linked_title)
        for link in title.linked_title_links
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
    "/{title_id}/tmdb/{tmdb_title_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_title_to_tmdb(
    session: SessionDep,
    title: ExistingTitle,
    tmdb_title: AdminTmdbTitle,
) -> TitlePublic:
    """Add the canonical title an admin chose to what a `Title` stands for.

    Its own endpoint rather than part of the update, because the link is a row of
    its own and what it drags along - the episodes being read again against the
    title chosen - is not something a write of the title's own columns does.

    Added to whatever the row already stands for rather than put in its place,
    since one page holding two titles is a thing websites do. Taking one off is
    `admin_unlink_title_from_tmdb`.
    """
    return _title_output(
        old_link_title_to_tmdb_title(session, title, tmdb_title),
    )


# TODO: Validate
@titles_router.put(
    "/{title_id}/tmdb-by-url",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_title_by_tmdb_url(
    session: SessionDep,
    title: ExistingTitle,
    url_input: TitleTmdbUrlInput,
) -> TitlePublic:
    return _title_output(
        old_link_title_to_tmdb_title_from_url(session, title, url_input.url),
    )


# TODO: Validate
@titles_router.post(
    "/{title_id}/linked-by-url",  # noqa: FAST003 - Used by the dependencies.
)
def admin_link_linked_title_by_url(
    session: SessionDep,
    title: ExistingTitle,
    url_input: TitleImportUrlInput,
) -> TitlePublic:
    return _title_output(
        old_import_linked_title_from_url(session, title, url_input.url),
    )


# TODO: Validate
@titles_router.delete(
    "/{title_id}/tmdb/{tmdb_title_id}",  # noqa: FAST003 - Used by the dependencies.
)
def admin_unlink_title_from_tmdb(
    session: SessionDep,
    title: ExistingTitle,
    tmdb_title: AdminTmdbTitle,
) -> TitlePublic:
    """Take one canonical title off what a `Title` stands for."""
    return _title_output(
        old_unlink_title_from_tmdb_title(session, title, tmdb_title),
    )


# TODO: Validate
@titles_router.post(
    "/{title_id}/unlink",  # noqa: FAST003 - Used by ExistingTitle.
)
def admin_unlink_title(session: SessionDep, title: ExistingTitle) -> TitlePublic:
    return _title_output(old_make_title_unlinked(session, title))


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
    return _title_output(old_relink_title(session, title))


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
@tmdb_titles_router.get("")
def get_tmdb_titles(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ReadOptions, Query()],
) -> TmdbTitlesPublic:
    """Get every `Title`."""
    return tmdb_list_response(
        session=session,
        base=select(Title).where(is_not_linked(Title)),
        response_model=TmdbTitlesPublic,
        schema=TmdbTitleOutput,
        read_options=read_options,
        current_user=current_user,
    )


router = APIRouter()


router.include_router(tmdb_titles_router)


router.include_router(titles_router)
