# TODO: Validate
"""Issue report routes."""

from fastapi import APIRouter, Depends

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.episodes.dependencies import ReadableEpisode
from app.issue_reports.dependencies import (
    EditableEpisodeIssueReport,
    EditableSeasonIssueReport,
    EditableShowIssueReport,
)
from app.issue_reports.schemas import (
    IssueReportCreate,
    IssueReportListOutput,
    IssueReportMediaType,
    IssueReportOutput,
    IssueReportUpdate,
)
from app.issue_reports.service import (
    create_issue_report,
    delete_issue_report_record,
    episode_issue_report,
    list_all_issue_reports,
    list_episode_issue_reports,
    list_season_issue_reports,
    list_show_issue_reports,
    season_issue_report,
    show_issue_report,
    update_issue_report_record,
)
from app.schemas import Message
from app.seasons.dependencies import ReadableSeason
from app.shows.dependencies import ReadableShow
from app.users.dependencies import OptionalUser

episode_issue_reports_router = APIRouter(
    prefix="/episodes/{episode_id}/issue-reports",
    tags=["issue reports"],
)
season_issue_reports_router = APIRouter(
    prefix="/seasons/{season_id}/issue-reports",
    tags=["issue reports"],
)
show_issue_reports_router = APIRouter(
    prefix="/shows/{show_id}/issue-reports",
    tags=["issue reports"],
)
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
issue_reports_router = APIRouter(prefix="/issue-reports", tags=["issue reports"])


# TODO: Validate
@episode_issue_reports_router.get("")
def get_episode_issue_reports(
    session: SessionDep,
    episode: ReadableEpisode,
) -> list[IssueReportOutput]:
    """Get every `EpisodeIssueReport` left on an `Episode`."""
    return list_episode_issue_reports(session, episode.id)


# TODO: Validate
@episode_issue_reports_router.post("")
def create_episode_issue_report(
    session: SessionDep,
    optional_user: OptionalUser,
    episode: ReadableEpisode,
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
    season: ReadableSeason,
) -> list[IssueReportOutput]:
    """Get every `SeasonIssueReport` left on a `Season`."""
    return list_season_issue_reports(session, season.id)


# TODO: Validate
@season_issue_reports_router.post("")
def create_season_issue_report(
    session: SessionDep,
    optional_user: OptionalUser,
    season: ReadableSeason,
    report_input: IssueReportCreate,
) -> IssueReportOutput:
    """Leave a `SeasonIssueReport` on a `Season`, with or without an account."""
    return create_issue_report(
        session,
        season_issue_report(optional_user, report_input, season.id),
    )


# TODO: Validate
@show_issue_reports_router.get("")
def get_show_issue_reports(
    session: SessionDep,
    show: ReadableShow,
) -> list[IssueReportOutput]:
    """Get every `ShowIssueReport` left on a `Show`."""
    return list_show_issue_reports(session, show.id)


# TODO: Validate
@show_issue_reports_router.post("")
def create_show_issue_report(
    session: SessionDep,
    optional_user: OptionalUser,
    show: ReadableShow,
    report_input: IssueReportCreate,
) -> IssueReportOutput:
    """Leave a `ShowIssueReport` on a `Show`, with or without an account."""
    return create_issue_report(
        session,
        show_issue_report(optional_user, report_input, show.id),
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


# TODO: Validate
@issue_reports_router.get("", dependencies=[Depends(get_current_active_superuser)])
def get_issue_reports(
    session: SessionDep,
    media_type: IssueReportMediaType | None = None,
) -> list[IssueReportListOutput]:
    """Get every issue report on the site, newest first."""
    return list_all_issue_reports(session, media_type)


router = APIRouter()
router.include_router(issue_reports_router)
router.include_router(episode_issue_reports_router)
router.include_router(season_issue_reports_router)
router.include_router(show_issue_reports_router)
router.include_router(episode_issue_report_router)
router.include_router(season_issue_report_router)
router.include_router(show_issue_report_router)
