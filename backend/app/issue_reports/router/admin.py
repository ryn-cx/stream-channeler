# TODO: Validate


"""Issue report routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.issue_reports.models import IssueReportKind, TitleIssueReport
from app.issue_reports.schemas import (
    IssueReportListOutput,
    IssueReportMediaType,
    IssueReportResolve,
)
from app.issue_reports.service.listing import list_all_issue_reports
from app.issue_reports.service.reports import resolve_title_issue_report
from app.schemas import Message

issue_reports_router = APIRouter(
    prefix="/issue-reports",
    tags=["issue reports"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@issue_reports_router.get("")
def get_issue_reports(
    session: SessionDep,
    media_type: IssueReportMediaType | None = None,
    kind: IssueReportKind | None = None,
    *,
    include_deleted: bool = True,
) -> list[IssueReportListOutput]:
    """Get every issue report on the site, newest first."""
    return list_all_issue_reports(
        session,
        media_type,
        kind,
        include_deleted=include_deleted,
    )


# TODO: Validate
@issue_reports_router.post("/titles/{issue_report_id}/resolve")
def resolve_title_report(
    session: SessionDep,
    issue_report_id: Annotated[uuid.UUID, Path()],
    resolve_input: IssueReportResolve,
) -> Message:
    report = session.get(TitleIssueReport, issue_report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="TitleIssueReport not found")
    return resolve_title_issue_report(session, report, resolve_input.resolution)


router = APIRouter()
router.include_router(issue_reports_router)
