# TODO: Validate
"""Who the channel order routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.channel_orders.models import ChannelOrder
from app.models import Visibility
from app.users.models import User
from tests.app.helpers.admin_routes import MISSING, assert_admin_only
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.helpers.utils import build_random_model
from tests.app.users.utils import auth_headers, create_random_user

SIGNED_IN_ROUTES: list[tuple[Method, str]] = [
    ("post", "/channel-orders"),
    ("get", "/channel-orders/favorite-ids"),
]

EDIT_ROUTES: list[tuple[Method, str]] = [
    ("patch", ""),
    ("delete", ""),
]


# TODO: Validate
def create_order(
    session: Session,
    user: User | None = None,
    *,
    visibility: Visibility = Visibility.private,
) -> ChannelOrder:
    """Create a `ChannelOrder` owned by `user`, or by a stranger when given none."""
    owner = user or create_random_user(session)
    order = build_random_model(
        ChannelOrder,
        user_id=owner.id,
        visibility=visibility,
        anonymous=False,
    )
    session.add(order)
    session.flush()
    return order


# TODO: Validate
def test_channel_order_admin_route_is_admin_only(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    assert_admin_only(
        session_scoped_client,
        session_scoped_session,
        "patch",
        f"/admin/channel-orders/{MISSING}",
    )


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), SIGNED_IN_ROUTES)
def test_channel_order_routes_that_only_need_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_requires_authentication(session_scoped_client, method, path, body={})
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, method, path, auth_headers(user), body={})


# TODO: Validate
def test_listing_public_channel_orders_is_open_to_anybody(
    session_scoped_client: TestClient,
) -> None:
    assert_allowed(
        session_scoped_client,
        "get",
        "/channel-orders",
        params={"scope": "public"},
    )


# TODO: Validate
def test_featured_channel_orders_are_open_to_anybody(
    session_scoped_client: TestClient,
) -> None:
    assert_allowed(session_scoped_client, "get", "/channel-orders/featured")


# TODO: Validate
def test_reading_a_public_channel_order_is_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    order = create_order(session_scoped_session, visibility=Visibility.public)
    assert_allowed(session_scoped_client, "get", f"/channel-orders/{order.id}")


# TODO: Validate
def test_reading_a_private_channel_order_refuses_a_stranger(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    order = create_order(session_scoped_session)
    path = f"/channel-orders/{order.id}"
    assert_requires_authentication(session_scoped_client, "get", path)
    stranger = create_random_user(session_scoped_session)
    assert_forbidden(session_scoped_client, "get", path, auth_headers(stranger))


# TODO: Validate
@pytest.mark.parametrize(("method", "suffix"), EDIT_ROUTES)
def test_channel_order_writes_refuse_everyone_but_the_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    suffix: str,
) -> None:
    order = create_order(session_scoped_session, visibility=Visibility.public)
    path = f"/channel-orders/{order.id}{suffix}"
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
def test_channel_order_writes_allow_its_owner(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    suffix: str,
) -> None:
    owner = create_random_user(session_scoped_session)
    order = create_order(session_scoped_session, owner)
    assert_allowed(
        session_scoped_client,
        method,
        f"/channel-orders/{order.id}{suffix}",
        auth_headers(owner),
        body={},
    )


# TODO: Validate
@pytest.mark.parametrize("suffix", ["/favorite", "/copy"])
def test_favoriting_and_copying_need_a_readable_order(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    suffix: str,
) -> None:
    order = create_order(session_scoped_session)
    path = f"/channel-orders/{order.id}{suffix}"
    assert_requires_authentication(session_scoped_client, "post", path, body={})
    stranger = create_random_user(session_scoped_session)
    assert_forbidden(
        session_scoped_client,
        "post",
        path,
        auth_headers(stranger),
        body={},
    )
