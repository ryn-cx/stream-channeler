# TODO: Validate
"""Issue report services."""

import uuid

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.issue_reports.models import (
    EpisodeIssueReport,
    SeasonIssueReport,
    ShowIssueReport,
)
from app.issue_reports.schemas import (
    IssueReportCreate,
    IssueReportListOutput,
    IssueReportMediaType,
    IssueReportOutput,
    IssueReportUpdate,
)
from app.schemas import Message
from app.seasons.models import Season
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User

type AnyIssueReport = EpisodeIssueReport | SeasonIssueReport | ShowIssueReport


# TODO: Validate
def _output(report: AnyIssueReport) -> IssueReportOutput:
    return IssueReportOutput.model_validate(report, from_attributes=True)


# TODO: Validate
def list_episode_issue_reports(
    session: Session,
    episode_id: uuid.UUID,
) -> list[IssueReportOutput]:
    """Return the reports left on one `Episode`, oldest first."""
    statement = (
        select(EpisodeIssueReport)
        .where(EpisodeIssueReport.episode_id == episode_id)
        .options(selectinload(EpisodeIssueReport.user))  # type: ignore[arg-type]
        .order_by(col(EpisodeIssueReport.created_at))
    )
    return [_output(report) for report in session.exec(statement).all()]


# TODO: Validate
def list_season_issue_reports(
    session: Session,
    season_id: uuid.UUID,
) -> list[IssueReportOutput]:
    """Return the reports left on one `Season`, oldest first."""
    statement = (
        select(SeasonIssueReport)
        .where(SeasonIssueReport.season_id == season_id)
        .options(selectinload(SeasonIssueReport.user))  # type: ignore[arg-type]
        .order_by(col(SeasonIssueReport.created_at))
    )
    return [_output(report) for report in session.exec(statement).all()]


# TODO: Validate
def list_show_issue_reports(
    session: Session,
    show_id: uuid.UUID,
) -> list[IssueReportOutput]:
    """Return the reports left on one `Show`, oldest first."""
    statement = (
        select(ShowIssueReport)
        .where(ShowIssueReport.show_id == show_id)
        .options(selectinload(ShowIssueReport.user))  # type: ignore[arg-type]
        .order_by(col(ShowIssueReport.created_at))
    )
    return [_output(report) for report in session.exec(statement).all()]


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


# TODO: Validate
def _episode_reports(session: Session) -> list[IssueReportListOutput]:
    statement = (
        select(EpisodeIssueReport, Episode, Season, Show, Source)
        .join(Episode, onclause=col(EpisodeIssueReport.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .options(selectinload(EpisodeIssueReport.user))  # type: ignore[arg-type]
    )
    return [
        IssueReportListOutput.model_validate(
            report,
            from_attributes=True,
            update={
                "media_type": IssueReportMediaType.episode,
                "media_id": episode.id,
                "media_name": episode.name,
                "season_name": season.name,
                "show_name": show.name,
                "source_name": source.name,
            },
        )
        for report, episode, season, show, source in session.exec(statement).all()
    ]


# TODO: Validate
def _season_reports(session: Session) -> list[IssueReportListOutput]:
    statement = (
        select(SeasonIssueReport, Season, Show, Source)
        .join(Season, onclause=col(SeasonIssueReport.season_id) == Season.id)
        .join(Show, onclause=col(Season.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .options(selectinload(SeasonIssueReport.user))  # type: ignore[arg-type]
    )
    return [
        IssueReportListOutput.model_validate(
            report,
            from_attributes=True,
            update={
                "media_type": IssueReportMediaType.season,
                "media_id": season.id,
                "media_name": season.name,
                "season_name": season.name,
                "show_name": show.name,
                "source_name": source.name,
            },
        )
        for report, season, show, source in session.exec(statement).all()
    ]


# TODO: Validate
def _show_reports(session: Session) -> list[IssueReportListOutput]:
    statement = (
        select(ShowIssueReport, Show, Source)
        .join(Show, onclause=col(ShowIssueReport.show_id) == Show.id)
        .join(Source, onclause=col(Show.source_id) == Source.id)
        .options(selectinload(ShowIssueReport.user))  # type: ignore[arg-type]
    )
    return [
        IssueReportListOutput.model_validate(
            report,
            from_attributes=True,
            update={
                "media_type": IssueReportMediaType.show,
                "media_id": show.id,
                "media_name": show.name,
                "season_name": None,
                "show_name": show.name,
                "source_name": source.name,
            },
        )
        for report, show, source in session.exec(statement).all()
    ]


# TODO: Validate
def list_all_issue_reports(
    session: Session,
    media_type: IssueReportMediaType | None = None,
) -> list[IssueReportListOutput]:
    """Return every report on the site, newest first, with the record it is on."""
    reports: list[IssueReportListOutput] = []
    if media_type in (None, IssueReportMediaType.episode):
        reports.extend(_episode_reports(session))
    if media_type in (None, IssueReportMediaType.season):
        reports.extend(_season_reports(session))
    if media_type in (None, IssueReportMediaType.show):
        reports.extend(_show_reports(session))
    reports.sort(key=lambda report: report.created_at, reverse=True)
    return reports
