# TODO: Validate
"""Who the channel routes let through.

A `Channel` is somebody's, so its routes split three ways: an owner may edit it,
anyone who can see it may read it, and only an admin may touch the admin ones.
What each route then does is the channel service's own and is tested there.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models import Visibility
from tests.app.channels.utils import create_random_channel
from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.users.utils import (
    auth_headers,
    create_random_superuser,
    create_random_user,
)

ADMIN_ROUTES: list[tuple[Method, str]] = [
    ("post", "/admin/channels"),
    ("patch", f"/admin/channels/{MISSING}"),
    ("get", "/admin/channels/queue"),
    ("patch", f"/admin/channels/queue/{MISSING}"),
    ("delete", f"/admin/channels/queue/{MISSING}"),
]

# Reads of a channel: open to anybody while the channel is public, the owner's
# alone while it is private.
READ_PATHS = [
    "",
    "/combined-channels",
    "/episodes",
    "/shows",
    "/sources",
]

# Writes to a channel, which are the owner's alone whatever its visibility.
EDIT_ROUTES: list[tuple[Method, str]] = [
    ("patch", ""),
    ("delete", ""),
    ("put", "/combined-channels"),
    ("post", "/blacklist-episode"),
    ("patch", "/default-order"),
    ("patch", "/order"),
    ("get", "/import-queue"),
    ("post", "/import-queue"),
    ("delete", f"/import-queue/{MISSING}"),
    ("delete", "/clear-completed-import-queue"),
]

# Routes that need an account but no channel of one's own.
SIGNED_IN_ROUTES: list[tuple[Method, str]] = [
    ("post", "/channels"),
    ("post", "/channels/bulk-import-queue"),
    ("get", "/channels/favorite-ids"),
]


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), ADMIN_ROUTES)
def test_channel_admin_routes_are_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_admin_only(session_scoped_client, session_scoped_session, method, path)


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), SIGNED_IN_ROUTES)
def test_channel_routes_that_only_need_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_requires_authentication(session_scoped_client, method, path, body={})
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, method, path, auth_headers(user), body={})


# TODO: Validate
def test_sort_options_are_open_to_anybody(session_scoped_client: TestClient) -> None:
    assert_allowed(session_scoped_client, "get", "/channels/sort-options")


# TODO: Validate
def test_listing_public_channels_is_open_to_anybody(
    session_scoped_client: TestClient,
) -> None:
    assert_allowed(
        session_scoped_client,
        "get",
        "/channels",
        params={"scope": "public"},
    )


# TODO: Validate
def test_listing_your_own_channels_needs_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    assert_requires_authentication(session_scoped_client, "get", "/channels")
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, "get", "/channels", auth_headers(user))


# TODO: Validate
@pytest.mark.parametrize("suffix", READ_PATHS)
def test_public_channel_reads_are_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    suffix: str,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    assert_allowed(session_scoped_client, "get", f"/channels/{channel.id}{suffix}")


# TODO: Validate
@pytest.mark.parametrize("suffix", READ_PATHS)
def test_private_channel_reads_refuse_a_stranger(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    suffix: str,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.private,
    )
    path = f"/channels/{channel.id}{suffix}"
    assert_requires_authentication(session_scoped_client, "get", path)
    stranger = create_random_user(session_scoped_session)
    assert_forbidden(session_scoped_client, "get", path, auth_headers(stranger))


# TODO: Validate
@pytest.mark.parametrize("suffix", READ_PATHS)
def test_private_channel_reads_allow_its_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    suffix: str,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(
        session_scoped_session,
        user=owner,
        visibility=Visibility.private,
    )
    assert_allowed(
        session_scoped_client,
        "get",
        f"/channels/{channel.id}{suffix}",
        auth_headers(owner),
    )


# TODO: Validate
@pytest.mark.parametrize(("method", "suffix"), EDIT_ROUTES)
def test_channel_writes_refuse_everyone_but_the_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    suffix: str,
) -> None:
    # Public, so what turns the stranger away is the channel not being theirs
    # rather than them not being allowed to look at it.
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    path = f"/channels/{channel.id}{suffix}"
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
@pytest.mark.parametrize(("method", "suffix"), EDIT_ROUTES)
def test_channel_writes_allow_its_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    suffix: str,
) -> None:
    owner = create_random_user(session_scoped_session)
    channel = create_random_channel(session_scoped_session, user=owner)
    assert_allowed(
        session_scoped_client,
        method,
        f"/channels/{channel.id}{suffix}",
        auth_headers(owner),
        body={},
    )


# TODO: Validate
@pytest.mark.parametrize(("method", "suffix"), EDIT_ROUTES)
def test_channel_writes_allow_an_admin(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    suffix: str,
) -> None:
    channel = create_random_channel(session_scoped_session)
    admin = create_random_superuser(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        method,
        f"/channels/{channel.id}{suffix}",
        auth_headers(admin),
        body={},
    )


# TODO: Validate
def test_favoriting_needs_an_account_and_a_readable_channel(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    path = f"/channels/{channel.id}/favorite"
    assert_requires_authentication(session_scoped_client, "post", path)
    stranger = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, "post", path, auth_headers(stranger))


# TODO: Validate
def test_favoriting_refuses_a_channel_the_user_cannot_see(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.private,
    )
    stranger = create_random_user(session_scoped_session)
    assert_forbidden(
        session_scoped_client,
        "post",
        f"/channels/{channel.id}/favorite",
        auth_headers(stranger),
    )
