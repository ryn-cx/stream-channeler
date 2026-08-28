# TODO: Validate
"""Who the watch routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.episodes.utils import create_random_episode
from tests.app.helpers.admin_routes import assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.users.utils import auth_headers, create_random_user
from tests.app.watches.utils import create_random_watch

SIGNED_IN_ROUTES: list[tuple[Method, str]] = [
    ("get", "/watches"),
    ("get", "/watches/export"),
]

EDIT_METHODS: list[Method] = ["patch", "delete"]


# TODO: Validate
def test_relinking_watches_is_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    assert_admin_only(
        session_scoped_client,
        session_scoped_session,
        "post",
        "/watches/relink",
    )


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), SIGNED_IN_ROUTES)
def test_watch_routes_that_only_need_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_requires_authentication(session_scoped_client, method, path)
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, method, path, auth_headers(user))


# TODO: Validate
def test_recording_a_watch_needs_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    episode = create_random_episode(session_scoped_session)
    path = f"/episodes/{episode.id}/watches"
    assert_requires_authentication(session_scoped_client, "post", path, body={})
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "post",
        path,
        auth_headers(user),
        body={"watch_date": "2026-01-01T00:00:00Z", "verified": True},
    )


# TODO: Validate
@pytest.mark.parametrize("method", EDIT_METHODS)
def test_watch_writes_refuse_everyone_but_the_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
) -> None:
    watch = create_random_watch(session_scoped_session)
    path = f"/watches/{watch.id}"
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
@pytest.mark.parametrize("method", EDIT_METHODS)
def test_watch_writes_allow_its_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
) -> None:
    owner = create_random_user(session_scoped_session)
    watch = create_random_watch(session_scoped_session, watch_user=owner)
    assert_allowed(
        session_scoped_client,
        method,
        f"/watches/{watch.id}",
        auth_headers(owner),
        body={},
    )
