# TODO: Validate


"""Issue report routes."""

from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.episodes.dependencies import ExistingEpisode
from app.issue_reports.schemas import (
    IssueReportCreate,
    IssueReportOutput,
)
from app.issue_reports.service.listing import (
    list_episode_issue_reports,
    list_season_issue_reports,
    list_title_issue_reports,
)
from app.issue_reports.service.reports import (
    create_issue_report,
    episode_issue_report,
    season_issue_report,
    title_issue_report,
)
from app.seasons.dependencies import ExistingSeason
from app.titles.dependencies import ExistingTitle
from app.users.dependencies import OptionalUser

episode_issue_reports_router = APIRouter(
    prefix="/episodes/{episode_id}/issue-reports",
    tags=["issue reports"],
)


season_issue_reports_router = APIRouter(
    prefix="/seasons/{season_id}/issue-reports",
    tags=["issue reports"],
)


title_issue_reports_router = APIRouter(
    prefix="/titles/{title_id}/issue-reports",
    tags=["issue reports"],
)


# TODO: Validate
@episode_issue_reports_router.get("")
def get_episode_issue_reports(
    session: SessionDep,
    episode: ExistingEpisode,
) -> list[IssueReportOutput]:
    """Get every `EpisodeIssueReport` left on an `Episode`."""
    return list_episode_issue_reports(session, episode.id)


# TODO: Validate
@episode_issue_reports_router.post("")
def create_episode_issue_report(
    session: SessionDep,
    optional_user: OptionalUser,
    episode: ExistingEpisode,
    report_input: IssueReportCreate,
) -> IssueReportOutput:
    """Leave an `EpisodeIssueReport` on an `Episode`, with or without an account."""
    return create_issue_report(
        session,
        episode_issue_report(optional_user, report_input, episode.id),
    )


# TODO: Validate
@season_issue_reports_router.get("")
def get_season_issue_reports(
    session: SessionDep,
    season: ExistingSeason,
) -> list[IssueReportOutput]:
    """Get every `SeasonIssueReport` left on a `Season`."""
    return list_season_issue_reports(session, season.id)


# TODO: Validate
@season_issue_reports_router.post("")
def create_season_issue_report(
    session: SessionDep,
    optional_user: OptionalUser,
    season: ExistingSeason,
    report_input: IssueReportCreate,
) -> IssueReportOutput:
    """Leave a `SeasonIssueReport` on a `Season`, with or without an account."""
    return create_issue_report(
        session,
        season_issue_report(optional_user, report_input, season.id),
    )


# TODO: Validate
@title_issue_reports_router.get("")
def get_title_issue_reports(
    session: SessionDep,
    title: ExistingTitle,
) -> list[IssueReportOutput]:
    """Get every `TitleIssueReport` left on a `Title`."""
    return list_title_issue_reports(session, title.id)


# TODO: Validate
@title_issue_reports_router.post("")
def create_title_issue_report(
    session: SessionDep,
    optional_user: OptionalUser,
    title: ExistingTitle,
    report_input: IssueReportCreate,
) -> IssueReportOutput:
    """Leave a `TitleIssueReport` on a `Title`, with or without an account."""
    return create_issue_report(
        session,
        title_issue_report(optional_user, report_input, title.id),
    )


router = APIRouter()
router.include_router(episode_issue_reports_router)
router.include_router(season_issue_reports_router)
router.include_router(title_issue_reports_router)
