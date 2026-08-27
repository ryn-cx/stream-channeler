# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.canonical_media.metadata import canonical_season_of
from app.issue_reports.service import list_season_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.seasons.dependencies import ExistingSeason
from app.seasons.schemas import (
    SeasonInformationOutput,
    SeasonInformationSide,
)
from app.seasons.service import (
    _information_side,
)

"""Season router."""


seasons_router = APIRouter(prefix="/seasons", tags=["seasons"])


# TODO: Validate
@seasons_router.get("/{season_id}/information")  # noqa: FAST003 - Used by ExistingSeason.
def get_season_information(
    session: SessionDep,
    season: ExistingSeason,
) -> SeasonInformationOutput:
    """Return what the website and TMDB each say about a `Season`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    show = season.show
    source = show.source

    counterpart = canonical_season_of(session, season.id)
    tmdb: SeasonInformationSide | None = None
    if counterpart:
        canonical_season, canonical_show = counterpart
        tmdb = _information_side(
            TMDB_PLUGIN_KEY,
            canonical_season,
            canonical_show,
        )

    return SeasonInformationOutput(
        issue_reports=list_season_issue_reports(session, season.id),
        source=_information_side(
            source.name or source.plugin.name or source.plugin.key,
            season,
            show,
        ),
        tmdb=tmdb,
    )


router = APIRouter()


router.include_router(seasons_router)
