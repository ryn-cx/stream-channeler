# TODO: Validate


from typing import Any

from sqlmodel import Session

from app.canonical_media.metadata import canonical_season_of
from app.issue_reports.service import list_season_issue_reports
from app.plugins.identifiers import TMDB_PLUGIN_KEY
from app.plugins.models import Plugin
from app.schemas import ReadOptions
from app.seasons.models import Season
from app.seasons.schemas import (
    SeasonInformationOutput,
    SeasonInformationSide,
    SeasonListOutput,
    SeasonOutput,
    SeasonsPublic,
)
from app.service import list_response
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.models import Source
from app.sources.schemas import SourceListPublic
from app.users.models import User

SEASON_EXTRA_COLUMNS: dict[str, Any] = {
    "show_name": Show.name,
    "source_id": Show.source_id,
    "source_name": Source.name,
    "plugin_id": Source.plugin_id,
    "plugin_name": Plugin.name,
}


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
            source.name or source.plugin.name or source.plugin.key,
            season,
            show,
        ),
        tmdb=tmdb,
    )


# TODO: Validate
def season_list_output(
    session: Session,
    current_user: User,
    read_options: ReadOptions,
) -> SeasonsPublic:
    """Read one page of every `Season`."""
    return list_response(
        session=session,
        base=Season.select_with_plugin_eager(),
        response_model=SeasonsPublic,
        schema=SeasonListOutput,
        params=read_options,
        current_user=current_user,
        extra_columns=SEASON_EXTRA_COLUMNS,
    )
