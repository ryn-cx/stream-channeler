# TODO: Validate


"""Issue report routes."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.issue_reports.schemas import (
    IssueReportListOutput,
    IssueReportMediaType,
)
from app.issue_reports.service import (
    list_all_issue_reports,
)

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
) -> list[IssueReportListOutput]:
    """Get every issue report on the site, newest first."""
    return list_all_issue_reports(session, media_type)


router = APIRouter()
router.include_router(issue_reports_router)
