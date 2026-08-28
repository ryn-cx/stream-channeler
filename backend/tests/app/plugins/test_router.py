# TODO: Validate
"""Who the plugin routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_requires_authentication,
)
from tests.app.users.utils import auth_headers, create_random_user

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("post", "/plugins"),
    ("get", "/plugins"),
    ("get", f"/plugins/{MISSING}"),
    ("patch", f"/plugins/{MISSING}"),
    ("delete", f"/plugins/{MISSING}"),
]

# What a plugin can do is the same question for every `User`, so these need an
# account and nothing more.
SIGNED_IN_ROUTES: list[tuple[Method, str]] = [
    ("get", "/plugins/import-watch-history-information"),
    ("get", "/plugins/import-url-information"),
    ("get", "/plugins/search-information"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_plugin_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), SIGNED_IN_ROUTES)
def test_plugin_information_routes_need_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_requires_authentication(session_scoped_client, method, path)
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, method, path, auth_headers(user))


# TODO: Validate
def test_match_url_needs_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    path = "/plugins/match-url"
    params = {"url": "https://example.com/watch"}
    assert_requires_authentication(session_scoped_client, "get", path, params=params)
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "get",
        path,
        auth_headers(user),
        params=params,
    )
