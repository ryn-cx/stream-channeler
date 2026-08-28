# TODO: Validate
"""Who the utility routes let through."""

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import assert_admin_only
from tests.app.helpers.permissions import request


# TODO: Validate
def test_health_check_is_open_to_anybody(session_scoped_client: TestClient) -> None:
    response = request(session_scoped_client, "get", "/utils/health-check/")
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is True


# TODO: Validate
def test_test_email_is_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    assert_admin_only(
        session_scoped_client,
        session_scoped_session,
        "post",
        "/admin/utils/test-email/",
    )
