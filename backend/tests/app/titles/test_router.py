# TODO: Validate
"""Who the title routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import Method, assert_allowed
from tests.app.titles.utils import create_random_title
from tests.app.users.utils import auth_headers, create_random_user

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("get", "/titles"),
    ("get", "/titles/unvalidated"),
    ("get", "/titles/tmdb"),
    ("get", f"/titles/tmdb/{MISSING}"),
    ("get", f"/titles/{MISSING}"),
    ("get", f"/titles/{MISSING}/non-canonical"),
    ("get", f"/titles/{MISSING}/tmdb-episode-groups"),
    ("patch", f"/titles/{MISSING}"),
    ("put", f"/titles/{MISSING}/canonical/{MISSING}"),
    ("put", f"/titles/{MISSING}/tmdb-by-url"),
    ("post", f"/titles/{MISSING}/linked-by-url"),
    ("delete", f"/titles/{MISSING}/canonical/{MISSING}"),
    ("post", f"/titles/{MISSING}/unlink"),
    ("post", f"/titles/{MISSING}/validate"),
    ("post", f"/titles/{MISSING}/relink"),
    ("post", f"/titles/{MISSING}/force-update"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_title_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
def test_title_information_is_readable_by_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    title = create_random_title(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/titles/{title.id}/information")


# TODO: Validate
def test_title_information_is_readable_while_signed_in(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    title = create_random_title(session_scoped_session)
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "get",
        f"/titles/{title.id}/information",
        auth_headers(user),
    )
