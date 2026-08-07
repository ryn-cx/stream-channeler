# TODO: Validate
"""Issue report dependencies."""

import uuid
from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Path

from app.auth.dependencies import CurrentUser, SessionDep
from app.issue_reports.models import (
    EpisodeIssueReport,
    SeasonIssueReport,
    ShowIssueReport,
)

type AnyIssueReport = EpisodeIssueReport | SeasonIssueReport | ShowIssueReport


def editable_issue_report[ReportT: AnyIssueReport](
    model: type[ReportT],
) -> Callable[..., ReportT]:
    """Build a dependency returning the report if the `User` wrote it.

    A report left by a visitor with no account has no author to claim it, so only
    a superuser can edit or delete one.
    """

    def dependency(
        session: SessionDep,
        current_user: CurrentUser,
        record_id: Annotated[uuid.UUID, Path(alias="issue_report_id")],
    ) -> ReportT:
        report = session.get(model, record_id)
        if report is None:
            raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
        if current_user.is_superuser or (
            report.user_id is not None and report.user_id == current_user.id
        ):
            return report
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized to access this {model.__name__}",
        )

    return dependency


EditableEpisodeIssueReport = Annotated[
    EpisodeIssueReport,
    Depends(editable_issue_report(EpisodeIssueReport)),
]
EditableSeasonIssueReport = Annotated[
    SeasonIssueReport,
    Depends(editable_issue_report(SeasonIssueReport)),
]
EditableShowIssueReport = Annotated[
    ShowIssueReport,
    Depends(editable_issue_report(ShowIssueReport)),
]
