# TODO: Validate
"""Who the episode routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from tests.app.episodes.utils import create_random_episode
from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_requires_authentication,
)
from tests.app.users.utils import auth_headers, create_random_user

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("post", f"/seasons/{MISSING}/episodes"),
    ("get", "/episodes"),
    ("get", "/episodes/tmdb-matches"),
    ("get", "/episodes/unlocked"),
    ("get", "/episodes/duplicated-canonical-episodes"),
    ("get", "/episodes/canonical"),
    ("get", f"/episodes/canonical/{MISSING}"),
    ("get", f"/episodes/{MISSING}"),
    ("get", f"/episodes/{MISSING}/tmdb-choices"),
    ("put", f"/episodes/{MISSING}/tmdb-url"),
    ("put", f"/episodes/{MISSING}/canonical/{MISSING}"),
    ("delete", f"/episodes/{MISSING}/canonical/{MISSING}"),
    ("put", f"/episodes/{MISSING}/tmdb-unlink"),
    ("put", f"/episodes/{MISSING}/tmdb-absent"),
    ("put", f"/episodes/{MISSING}/verify-canonical-link"),
    ("patch", f"/episodes/{MISSING}"),
    ("delete", f"/episodes/{MISSING}"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_episode_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
@pytest.mark.parametrize("suffix", ["information", "non-canonical"])
def test_episode_reads_are_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    suffix: str,
) -> None:
    episode = create_random_episode(session_scoped_session)
    assert_allowed(session_scoped_client, "get", f"/episodes/{episode.id}/{suffix}")


# TODO: Validate
def test_setting_a_user_url_needs_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    episode = create_random_episode(session_scoped_session)
    path = f"/episodes/{episode.id}/user-url"
    assert_requires_authentication(
        session_scoped_client,
        "put",
        path,
        body={"url": "https://example.com/watch"},
    )
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "put",
        path,
        auth_headers(user),
        body={"url": "https://example.com/watch"},
    )


# TODO: Validate
def test_clearing_a_user_url_needs_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    episode = create_random_episode(session_scoped_session)
    path = f"/episodes/{episode.id}/user-url"
    assert_requires_authentication(session_scoped_client, "delete", path)
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, "delete", path, auth_headers(user))
