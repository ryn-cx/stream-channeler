# TODO: Validate


from sqlmodel import Session

from app.canonical_media.metadata import canonical_season_of
from app.issue_reports.service.listing import list_season_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInformationOutput,
    SeasonInformationSide,
    SeasonOutput,
)
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourceListPublic


# TODO: Validate
def _information_side(
    label: str,
    season: Season,
    show: Show,
) -> SeasonInformationSide:
    return SeasonInformationSide(
        label=label,
        season=SeasonOutput.model_validate(season),
        show=ShowPublic.model_validate(show),
        source=SourceListPublic.model_validate(show.source),
    )


# TODO: Validate
def season_information(session: Session, season: Season) -> SeasonInformationOutput:
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
        tmdb = _information_side(TMDB_PLUGIN_KEY, canonical_season, canonical_show)

    return SeasonInformationOutput(
        issue_reports=list_season_issue_reports(session, season.id),
        source=_information_side(
            source.name or source.plugin.key,
            season,
            show,
        ),
        tmdb=tmdb,
    )
