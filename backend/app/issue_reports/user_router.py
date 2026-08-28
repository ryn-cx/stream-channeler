# TODO: Validate


"""Issue report routes."""

from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.issue_reports.dependencies import (
    EditableEpisodeIssueReport,
    EditableSeasonIssueReport,
    EditableShowIssueReport,
)
from app.issue_reports.schemas import (
    IssueReportOutput,
    IssueReportUpdate,
)
from app.issue_reports.service import (
    delete_issue_report_record,
    update_issue_report_record,
)
from app.schemas import Message

episode_issue_report_router = APIRouter(
    prefix="/episode-issue-reports",
    tags=["issue reports"],
)


season_issue_report_router = APIRouter(
    prefix="/season-issue-reports",
    tags=["issue reports"],
)


show_issue_report_router = APIRouter(
    prefix="/show-issue-reports",
    tags=["issue reports"],
)


# TODO: Validate
@episode_issue_report_router.patch("/{issue_report_id}")  # noqa: FAST003 - Used by EditableEpisodeIssueReport.
def update_episode_issue_report(
    session: SessionDep,
    issue_report: EditableEpisodeIssueReport,
    report_input: IssueReportUpdate,
) -> IssueReportOutput:
    """Rewrite an `EpisodeIssueReport` the `User` left."""
    return update_issue_report_record(session, issue_report, report_input)


# TODO: Validate
@episode_issue_report_router.delete("/{issue_report_id}")  # noqa: FAST003 - Used by EditableEpisodeIssueReport.
def delete_episode_issue_report(
    session: SessionDep,
    issue_report: EditableEpisodeIssueReport,
) -> Message:
    """Drop an `EpisodeIssueReport` the `User` left."""
    return delete_issue_report_record(session, issue_report)


# TODO: Validate
@season_issue_report_router.patch("/{issue_report_id}")  # noqa: FAST003 - Used by EditableSeasonIssueReport.
def update_season_issue_report(
    session: SessionDep,
    issue_report: EditableSeasonIssueReport,
    report_input: IssueReportUpdate,
) -> IssueReportOutput:
    """Rewrite a `SeasonIssueReport` the `User` left."""
    return update_issue_report_record(session, issue_report, report_input)


# TODO: Validate
@season_issue_report_router.delete("/{issue_report_id}")  # noqa: FAST003 - Used by EditableSeasonIssueReport.
def delete_season_issue_report(
    session: SessionDep,
    issue_report: EditableSeasonIssueReport,
) -> Message:
    """Drop a `SeasonIssueReport` the `User` left."""
    return delete_issue_report_record(session, issue_report)


# TODO: Validate
@show_issue_report_router.patch("/{issue_report_id}")  # noqa: FAST003 - Used by EditableShowIssueReport.
def update_show_issue_report(
    session: SessionDep,
    issue_report: EditableShowIssueReport,
    report_input: IssueReportUpdate,
) -> IssueReportOutput:
    """Rewrite a `ShowIssueReport` the `User` left."""
    return update_issue_report_record(session, issue_report, report_input)


# TODO: Validate
@show_issue_report_router.delete("/{issue_report_id}")  # noqa: FAST003 - Used by EditableShowIssueReport.
def delete_show_issue_report(
    session: SessionDep,
    issue_report: EditableShowIssueReport,
) -> Message:
    """Drop a `ShowIssueReport` the `User` left."""
    return delete_issue_report_record(session, issue_report)


router = APIRouter()
router.include_router(episode_issue_report_router)
router.include_router(season_issue_report_router)
router.include_router(show_issue_report_router)
