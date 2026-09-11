# TODO: Validate


from sqlmodel import Session

from app.issue_reports.service.listing import list_season_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInformationOutput,
    SeasonInformationSide,
    SeasonOutput,
)
from app.sources.schemas import SourceListPublic
from app.titles.models import Title
from app.titles.schemas import TitlePublic
from app.tmdb_media.metadata import tmdb_season_of


# TODO: Validate
def _information_side(
    label: str,
    season: Season,
    title: Title,
) -> SeasonInformationSide:
    return SeasonInformationSide(
        label=label,
        season=SeasonOutput.model_validate(season),
        title=TitlePublic.model_validate(title),
        source=SourceListPublic.model_validate(title.source),
    )


# TODO: Validate
def season_information(session: Session, season: Season) -> SeasonInformationOutput:
    """Return what the website and TMDB each say about a `Season`.

    The website's own account is what it stored rather than what is served, since
    what is served already reads as TMDB has it and would leave nothing to
    compare.
    """
    title = season.title
    source = title.source

    counterpart = tmdb_season_of(session, season.id)
    tmdb: SeasonInformationSide | None = None
    if counterpart:
        tmdb_season, tmdb_title = counterpart
        tmdb = _information_side(TMDB_PLUGIN_KEY, tmdb_season, tmdb_title)

    return SeasonInformationOutput(
        issue_reports=list_season_issue_reports(session, season.id),
        source=_information_side(
            source.key,
            season,
            title,
        ),
        tmdb=tmdb,
    )
