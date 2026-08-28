# TODO: Validate
"""Who the issue report routes let through.

A report can be left without an account, which is the point of them: somebody who
has spotted that an episode is wrong should not have to sign up to say so. Only
editing one afterwards is limited to whoever left it.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.issue_reports.models import (
    EpisodeIssueReport,
    SeasonIssueReport,
    ShowIssueReport,
)
from app.users.models import User
from tests.app.episodes.utils import create_random_episode
from tests.app.helpers.admin_routes import assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.helpers.utils import random_lower_string
from tests.app.seasons.utils import create_random_season
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import auth_headers, create_random_user

EDIT_METHODS: list[Method] = ["patch", "delete"]


# TODO: Validate
def test_listing_every_issue_report_is_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    assert_admin_only(
        session_scoped_client,
        session_scoped_session,
        "get",
        "/issue-reports",
    )


# TODO: Validate
def test_reading_an_episodes_issue_reports_is_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    episode = create_random_episode(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "get",
        f"/episodes/{episode.id}/issue-reports",
    )


# TODO: Validate
def test_reading_a_seasons_issue_reports_is_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    season = create_random_season(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/seasons/{season.id}/issue-reports")


# TODO: Validate
def test_reading_a_shows_issue_reports_is_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    show = create_random_show(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/shows/{show.id}/issue-reports")


# TODO: Validate
def test_leaving_an_issue_report_needs_no_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    episode = create_random_episode(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "post",
        f"/episodes/{episode.id}/issue-reports",
        body={"report": random_lower_string()},
    )


# TODO: Validate
def episode_report(session: Session, author: User) -> EpisodeIssueReport:
    report = EpisodeIssueReport(
        episode_id=create_random_episode(session).id,
        user_id=author.id,
        report=random_lower_string(),
    )
    session.add(report)
    session.flush()
    return report


# TODO: Validate
def season_report(session: Session, author: User) -> SeasonIssueReport:
    report = SeasonIssueReport(
        season_id=create_random_season(session).id,
        user_id=author.id,
        report=random_lower_string(),
    )
    session.add(report)
    session.flush()
    return report


# TODO: Validate
def show_report(session: Session, author: User) -> ShowIssueReport:
    report = ShowIssueReport(
        show_id=create_random_show(session).id,
        user_id=author.id,
        report=random_lower_string(),
    )
    session.add(report)
    session.flush()
    return report


REPORTS = [
    ("episode-issue-reports", episode_report),
    ("season-issue-reports", season_report),
    ("show-issue-reports", show_report),
]


# TODO: Validate
@pytest.mark.parametrize(("prefix", "factory"), REPORTS)
@pytest.mark.parametrize("method", EDIT_METHODS)
def test_editing_a_report_refuses_everyone_but_its_author(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    prefix: str,
    factory: object,
) -> None:
    author = create_random_user(session_scoped_session)
    report = factory(session_scoped_session, author)  # type: ignore[operator]
    path = f"/{prefix}/{report.id}"
    assert_requires_authentication(session_scoped_client, method, path, body={})
    stranger = create_random_user(session_scoped_session)
    assert_forbidden(
        session_scoped_client,
        method,
        path,
        auth_headers(stranger),
        body={},
    )


# TODO: Validate
@pytest.mark.parametrize(("prefix", "factory"), REPORTS)
@pytest.mark.parametrize("method", EDIT_METHODS)
def test_editing_a_report_allows_its_author(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    prefix: str,
    factory: object,
) -> None:
    author = create_random_user(session_scoped_session)
    report = factory(session_scoped_session, author)  # type: ignore[operator]
    assert_allowed(
        session_scoped_client,
        method,
        f"/{prefix}/{report.id}",
        auth_headers(author),
        body={"report": random_lower_string()},
    )
