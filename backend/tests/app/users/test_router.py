# TODO: Validate
"""Who the user routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.helpers.utils import random_email, random_lower_string
from tests.app.users.utils import (
    auth_headers,
    create_random_superuser,
    create_random_user,
)

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("get", "/admin/users"),
    ("post", "/admin/users"),
    ("get", f"/admin/users/{MISSING}/channels"),
    ("patch", f"/admin/users/{MISSING}"),
    ("delete", f"/admin/users/{MISSING}"),
]

OWN_ACCOUNT_ROUTES: list[tuple[Method, str]] = [
    ("get", "/users/me"),
    ("patch", "/users/me"),
    ("get", "/users/me/source-preferences"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_user_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), OWN_ACCOUNT_ROUTES)
def test_own_account_routes_need_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_requires_authentication(session_scoped_client, method, path, body={})
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, method, path, auth_headers(user), body={})


# TODO: Validate
def test_signup_is_open_to_anybody(session_scoped_client: TestClient) -> None:
    assert_allowed(
        session_scoped_client,
        "post",
        "/users/signup",
        body={
            "email": random_email(),
            "username": random_lower_string(),
            "password": random_lower_string(),
        },
    )


# TODO: Validate
def test_a_users_public_channels_are_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/users/{user.id}/channels")


# TODO: Validate
def test_reading_another_user_is_refused(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    subject = create_random_user(session_scoped_session)
    stranger = create_random_user(session_scoped_session)
    path = f"/users/{subject.id}"
    assert_requires_authentication(session_scoped_client, "get", path)
    assert_forbidden(session_scoped_client, "get", path, auth_headers(stranger))


# TODO: Validate
def test_reading_yourself_by_id_is_allowed(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "get",
        f"/users/{user.id}",
        auth_headers(user),
    )


# TODO: Validate
def test_an_admin_may_read_any_user(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    subject = create_random_user(session_scoped_session)
    admin = create_random_superuser(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "get",
        f"/users/{subject.id}",
        auth_headers(admin),
    )
