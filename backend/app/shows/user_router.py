# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.canonical_media.metadata import (
    canonical_show_of,
    tmdb_show_url,
)
from app.issue_reports.service import list_show_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.shows.dependencies import AdminCanonicalShow, ExistingShow
from app.shows.schemas import (
    CanonicalShowOutput,
    ShowInformationOutput,
    ShowInformationSide,
)
from app.shows.service import (
    _information_side,
)
from app.users.dependencies import OptionalUser

"""Show router."""


canonical_shows_router = APIRouter(
    prefix="/shows/canonical",
    tags=["canonical-shows"],
)


shows_router = APIRouter(prefix="/shows", tags=["shows"])


# TODO: Validate
@shows_router.get("/{show_id}/information")  # noqa: FAST003 - Used by ExistingShow.
def get_show_information(
    session: SessionDep,
    show: ExistingShow,
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

    editable = current_user is not None and current_user.is_superuser

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
@canonical_shows_router.get("/{canonical_show_id}")  # noqa: FAST003 - Used by AdminCanonicalShow.
def get_canonical_show_by_id(
    canonical_show: AdminCanonicalShow,
) -> CanonicalShowOutput:
    """Get a `Show`."""
    return CanonicalShowOutput.model_validate(canonical_show)


router = APIRouter()


router.include_router(canonical_shows_router)


router.include_router(shows_router)
