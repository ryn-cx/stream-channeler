# TODO: Validate
"""Who the comment routes let through."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.comments.models import Comment
from app.models import Visibility
from app.users.models import User
from tests.app.channels.utils import create_random_channel
from tests.app.helpers.permissions import (
    Method,
    assert_allowed,
    assert_forbidden,
    assert_requires_authentication,
)
from tests.app.helpers.utils import random_lower_string
from tests.app.users.utils import auth_headers, create_random_user

SIGNED_IN_ROUTES: list[tuple[Method, str]] = [
    ("get", "/comments/mine"),
    ("get", "/comments/unread-count"),
    ("post", "/comments/read"),
]

EDIT_METHODS: list[Method] = ["patch", "delete"]


# TODO: Validate
def create_comment(session: Session, channel_id: object, author: User) -> Comment:
    """Leave a `Comment` on a channel, written by `author`."""
    comment = Comment(
        channel_id=channel_id,
        user_id=author.id,
        body=random_lower_string(),
    )
    session.add(comment)
    session.flush()
    return comment


# TODO: Validate
@pytest.mark.parametrize(("method", "path"), SIGNED_IN_ROUTES)
def test_comment_routes_that_only_need_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
    path: str,
) -> None:
    assert_requires_authentication(session_scoped_client, method, path)
    user = create_random_user(session_scoped_session)
    assert_allowed(session_scoped_client, method, path, auth_headers(user))


# TODO: Validate
def test_reading_a_public_channels_comments_is_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    assert_allowed(session_scoped_client, "get", f"/channels/{channel.id}/comments")


# TODO: Validate
def test_reading_a_private_channels_comments_refuses_a_stranger(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.private,
    )
    path = f"/channels/{channel.id}/comments"
    assert_requires_authentication(session_scoped_client, "get", path)
    stranger = create_random_user(session_scoped_session)
    assert_forbidden(session_scoped_client, "get", path, auth_headers(stranger))


# TODO: Validate
def test_leaving_a_comment_needs_an_account(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    path = f"/channels/{channel.id}/comments"
    assert_requires_authentication(
        session_scoped_client,
        "post",
        path,
        body={"body": random_lower_string()},
    )
    user = create_random_user(session_scoped_session)
    assert_allowed(
        session_scoped_client,
        "post",
        path,
        auth_headers(user),
        body={"body": random_lower_string()},
    )


# TODO: Validate
@pytest.mark.parametrize("method", EDIT_METHODS)
def test_editing_a_comment_refuses_everyone_but_its_author(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    author = create_random_user(session_scoped_session)
    comment = create_comment(session_scoped_session, channel.id, author)
    path = f"/comments/{comment.id}"
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
def test_editing_a_comment_allows_its_author(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
    method: Method,
) -> None:
    channel = create_random_channel(
        session_scoped_session,
        visibility=Visibility.public,
    )
    author = create_random_user(session_scoped_session)
    comment = create_comment(session_scoped_session, channel.id, author)
    assert_allowed(
        session_scoped_client,
        method,
        f"/comments/{comment.id}",
        auth_headers(author),
        body={"body": random_lower_string()},
    )
