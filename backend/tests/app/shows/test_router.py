# TODO: Validate
"""Who the show routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import Method, assert_allowed
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import auth_headers, create_random_user

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("post", f"/sources/{MISSING}/shows"),
    ("get", "/shows"),
    ("get", "/shows/unvalidated"),
    ("get", "/shows/canonical"),
    ("get", f"/shows/canonical/{MISSING}"),
    ("get", f"/shows/{MISSING}"),
    ("get", f"/shows/{MISSING}/non-canonical"),
    ("get", f"/shows/{MISSING}/tmdb-episode-groups"),
    ("patch", f"/shows/{MISSING}"),
    ("put", f"/shows/{MISSING}/canonical/{MISSING}"),
    ("put", f"/shows/{MISSING}/canonical-by-tmdb-url"),
    ("post", f"/shows/{MISSING}/non-canonical-by-url"),
    ("delete", f"/shows/{MISSING}/canonical/{MISSING}"),
    ("post", f"/shows/{MISSING}/canonicalize"),
    ("post", f"/shows/{MISSING}/validate"),
    ("post", f"/shows/{MISSING}/relink"),
    ("post", f"/shows/{MISSING}/force-update"),
    ("delete", f"/shows/{MISSING}"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_show_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
def test_show_information_is_readable_by_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    show = create_random_show(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/shows/{show.id}/information")


# TODO: Validate
def test_show_information_is_readable_while_signed_in(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    show = create_random_show(session_scoped_session)
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "get",
        f"/shows/{show.id}/information",
        auth_headers(user),
    )
