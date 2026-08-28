# TODO: Validate
"""Who the season routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import Method, assert_allowed
from tests.app.seasons.utils import create_random_season

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("post", f"/shows/{MISSING}/seasons"),
    ("get", "/seasons"),
    ("get", f"/seasons/{MISSING}"),
    ("patch", f"/seasons/{MISSING}"),
    ("delete", f"/seasons/{MISSING}"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_season_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
def test_season_information_is_readable_by_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    season = create_random_season(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/seasons/{season.id}/information")
