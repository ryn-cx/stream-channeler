# TODO: Validate
"""Who the file routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import Method

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("post", f"/admin/plugins/{MISSING}/files"),
    ("get", "/admin/files"),
    ("get", f"/admin/files/{MISSING}"),
    ("patch", f"/admin/files/{MISSING}"),
    ("delete", f"/admin/files/{MISSING}"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_file_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)
