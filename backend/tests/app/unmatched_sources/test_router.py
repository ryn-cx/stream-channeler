# TODO: Validate
"""Who the unmatched source routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import Method

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("get", "/unmatched-sources"),
    ("post", f"/unmatched-sources/{MISSING}/import"),
    ("post", f"/unmatched-sources/{MISSING}/ignore"),
    ("delete", f"/unmatched-sources/{MISSING}"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_unmatched_source_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)
