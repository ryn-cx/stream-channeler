# TODO: Validate
"""Issue report services."""

import uuid
from typing import Any

from sqlalchemy.orm import selectinload
from sqlmodel import Session, col, select

from app.episodes.models import Episode
from app.issue_reports.models import (
    EpisodeIssueReport,
    IssueReportKind,
    SeasonIssueReport,
    TitleIssueReport,
)
from app.issue_reports.schemas import (
    IssueReportListOutput,
    IssueReportMediaType,
    IssueReportOutput,
    IssueReportTmdbLink,
)
from app.issue_reports.service.reports import _output
from app.issue_reports.service.suggestions import suggested_title
from app.seasons.models import Season
from app.sources.models import Source
from app.titles.models import Title
from app.tmdb_media.tmdb import tmdb_title_url


# TODO: Validate
def list_episode_issue_reports(
    session: Session,
    episode_id: uuid.UUID,
) -> list[IssueReportOutput]:
    """Return the reports left on one `Episode`, oldest first."""
    statement = (
        select(EpisodeIssueReport)
        .where(
            EpisodeIssueReport.episode_id == episode_id,
            col(EpisodeIssueReport.deleted_at).is_(None),
        )
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
        .where(
            SeasonIssueReport.season_id == season_id,
            col(SeasonIssueReport.deleted_at).is_(None),
        )
        .options(selectinload(SeasonIssueReport.user))  # type: ignore[arg-type]
        .order_by(col(SeasonIssueReport.created_at))
    )
    return [_output(report) for report in session.exec(statement).all()]


# TODO: Validate
def list_title_issue_reports(
    session: Session,
    title_id: uuid.UUID,
) -> list[IssueReportOutput]:
    """Return the reports left on one `Title`, oldest first."""
    statement = (
        select(TitleIssueReport)
        .where(
            TitleIssueReport.title_id == title_id,
            col(TitleIssueReport.deleted_at).is_(None),
        )
        .options(selectinload(TitleIssueReport.user))  # type: ignore[arg-type]
        .order_by(col(TitleIssueReport.created_at))
    )
    return [_output(report) for report in session.exec(statement).all()]


# TODO: Validate
def _report_filters(
    model: type[EpisodeIssueReport | SeasonIssueReport | TitleIssueReport],
    kind: IssueReportKind | None,
    *,
    include_deleted: bool,
) -> list[Any]:
    filters: list[Any] = []
    if kind is not None:
        filters.append(col(model.kind) == kind)
    if not include_deleted:
        filters.append(col(model.deleted_at).is_(None))
    return filters


# TODO: Validate
def _current_links(title: Title) -> list[IssueReportTmdbLink]:
    return [
        IssueReportTmdbLink(
            id=tmdb_title.id,
            name=tmdb_title.name,
            year=tmdb_title.year,
            url=tmdb_title_url(tmdb_title.key),
        )
        for tmdb_title in title.tmdb_titles
    ]


# TODO: Validate
def _episode_reports(
    session: Session,
    kind: IssueReportKind | None,
    *,
    include_deleted: bool,
) -> list[IssueReportListOutput]:
    statement = (
        select(EpisodeIssueReport, Episode, Season, Title, Source)
        .join(Episode, onclause=col(EpisodeIssueReport.episode_id) == Episode.id)
        .join(Season, onclause=col(Episode.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .where(
            *_report_filters(
                EpisodeIssueReport,
                kind,
                include_deleted=include_deleted,
            ),
        )
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
                "title_name": title.name,
                "source_key": source.key,
            },
        )
        for report, episode, season, title, source in session.exec(statement).all()
    ]


# TODO: Validate
def _season_reports(
    session: Session,
    kind: IssueReportKind | None,
    *,
    include_deleted: bool,
) -> list[IssueReportListOutput]:
    statement = (
        select(SeasonIssueReport, Season, Title, Source)
        .join(Season, onclause=col(SeasonIssueReport.season_id) == Season.id)
        .join(Title, onclause=col(Season.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .where(
            *_report_filters(
                SeasonIssueReport,
                kind,
                include_deleted=include_deleted,
            ),
        )
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
                "title_name": title.name,
                "source_key": source.key,
            },
        )
        for report, season, title, source in session.exec(statement).all()
    ]


# TODO: Validate
def _title_reports(
    session: Session,
    kind: IssueReportKind | None,
    *,
    include_deleted: bool,
) -> list[IssueReportListOutput]:
    statement = (
        select(TitleIssueReport, Title, Source)
        .join(Title, onclause=col(TitleIssueReport.title_id) == Title.id)
        .join(Source, onclause=col(Title.source_id) == Source.id)
        .where(
            *_report_filters(
                TitleIssueReport,
                kind,
                include_deleted=include_deleted,
            ),
        )
        .options(selectinload(TitleIssueReport.user))  # type: ignore[arg-type]
    )
    return [
        IssueReportListOutput.model_validate(
            report,
            from_attributes=True,
            update={
                "media_type": IssueReportMediaType.title,
                "media_id": title.id,
                "media_name": title.name,
                "season_name": None,
                "title_name": title.name,
                "source_key": source.key,
                "current_links": _current_links(title),
                "suggestion": suggested_title(report.report),
            },
        )
        for report, title, source in session.exec(statement).all()
    ]


# TODO: Validate
def list_all_issue_reports(
    session: Session,
    media_type: IssueReportMediaType | None = None,
    kind: IssueReportKind | None = None,
    *,
    include_deleted: bool = True,
) -> list[IssueReportListOutput]:
    """Return every report on the site, newest first, with the record it is on."""
    reports: list[IssueReportListOutput] = []
    if media_type in (None, IssueReportMediaType.episode):
        reports.extend(
            _episode_reports(session, kind, include_deleted=include_deleted),
        )
    if media_type in (None, IssueReportMediaType.season):
        reports.extend(
            _season_reports(session, kind, include_deleted=include_deleted),
        )
    if media_type in (None, IssueReportMediaType.title):
        reports.extend(
            _title_reports(session, kind, include_deleted=include_deleted),
        )
    reports.sort(key=lambda report: report.created_at, reverse=True)
    return reports
