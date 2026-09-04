# TODO: Validate
"""Issue report services."""

import uuid

from sqlmodel import Session

from app.issue_reports.models import (
    EpisodeIssueReport,
    SeasonIssueReport,
    ShowIssueReport,
)
from app.issue_reports.schemas import (
    IssueReportCreate,
    IssueReportOutput,
    IssueReportUpdate,
)
from app.schemas import Message
from app.users.models import User

type AnyIssueReport = EpisodeIssueReport | SeasonIssueReport | ShowIssueReport


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
        user_id=user.id if user else None,
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
        user_id=user.id if user else None,
        season_id=season_id,
    )


# TODO: Validate
def show_issue_report(
    user: User | None,
    report_input: IssueReportCreate,
    show_id: uuid.UUID,
) -> ShowIssueReport:
    """Build a report on a `Show`, on behalf of `user` when there is one."""
    return ShowIssueReport(
        report=report_input.report,
        user_id=user.id if user else None,
        show_id=show_id,
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
