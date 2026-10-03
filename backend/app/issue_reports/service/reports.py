# TODO: Validate
"""Issue report services."""

import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.issue_reports.models import (
    EpisodeIssueReport,
    SeasonIssueReport,
    TitleIssueReport,
)
from app.issue_reports.schemas import (
    IssueReportCreate,
    IssueReportOutput,
    IssueReportResolution,
    IssueReportUpdate,
)
from app.issue_reports.service.suggestions import suggested_title
from app.schemas import Message
from app.titles.service.linking import (
    old_link_title_to_tmdb_title,
    old_unlink_title_from_tmdb_title,
    tmdb_title_from_url,
)
from app.users.models import User
from app.utils import tz_datetime

type AnyIssueReport = EpisodeIssueReport | SeasonIssueReport | TitleIssueReport


# TODO: Validate
def _output(report: AnyIssueReport) -> IssueReportOutput:
    return IssueReportOutput.model_validate(report, from_attributes=True)


# TODO: Validate
def create_issue_report(
    session: Session,
    report: AnyIssueReport,
) -> IssueReportOutput:
    """Leave a report on one record."""
    session.add(report)
    session.commit()
    session.refresh(report)
    return _output(report)


# TODO: Validate
def episode_issue_report(
    user: User | None,
    report_input: IssueReportCreate,
    episode_id: uuid.UUID,
) -> EpisodeIssueReport:
    """Build a report on an `Episode`, on behalf of `user` when there is one."""
    return EpisodeIssueReport(
        report=report_input.report,
        kind=report_input.kind,
        user_id=None if report_input.anonymous or user is None else user.id,
        episode_id=episode_id,
    )


# TODO: Validate
def season_issue_report(
    user: User | None,
    report_input: IssueReportCreate,
    season_id: uuid.UUID,
) -> SeasonIssueReport:
    """Build a report on a `Season`, on behalf of `user` when there is one."""
    return SeasonIssueReport(
        report=report_input.report,
        kind=report_input.kind,
        user_id=None if report_input.anonymous or user is None else user.id,
        season_id=season_id,
    )


# TODO: Validate
def title_issue_report(
    user: User | None,
    report_input: IssueReportCreate,
    title_id: uuid.UUID,
) -> TitleIssueReport:
    """Build a report on a `Title`, on behalf of `user` when there is one."""
    return TitleIssueReport(
        report=report_input.report,
        kind=report_input.kind,
        user_id=None if report_input.anonymous or user is None else user.id,
        title_id=title_id,
    )


# TODO: Validate
def update_issue_report_record(
    session: Session,
    report: AnyIssueReport,
    report_input: IssueReportUpdate,
) -> IssueReportOutput:
    """Rewrite a report."""
    report.report = report_input.report
    session.add(report)
    session.commit()
    session.refresh(report)
    return _output(report)


# TODO: Validate
def delete_issue_report_record(session: Session, report: AnyIssueReport) -> Message:
    """Drop a report."""
    session.delete(report)
    session.commit()
    return Message(message="Issue report deleted successfully")


# TODO: Validate
def resolve_title_issue_report(
    session: Session,
    report: TitleIssueReport,
    resolution: IssueReportResolution,
) -> Message:
    if resolution != IssueReportResolution.ignore:
        suggestion = suggested_title(report.report)
        if suggestion is None:
            raise HTTPException(
                status_code=400,
                detail="This report does not suggest a title to link",
            )
        title = report.title
        suggested = tmdb_title_from_url(session, suggestion.url)
        old_link_title_to_tmdb_title(session, title, suggested)
        if resolution == IssueReportResolution.replace_links:
            for tmdb_title in list(title.tmdb_titles):
                if tmdb_title.id != suggested.id:
                    old_unlink_title_from_tmdb_title(session, title, tmdb_title)
    report.deleted_at = tz_datetime.now()
    session.add(report)
    session.commit()
    return Message(message="Issue report resolved")
