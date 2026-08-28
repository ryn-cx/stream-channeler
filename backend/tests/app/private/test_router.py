# TODO: Validate
"""Who the private routes let through."""

import uuid

from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.users.models import User
from tests.app.helpers.permissions import request
from tests.app.helpers.utils import random_email, random_lower_string


# TODO: Validate
def test_private_user_creation_is_open_to_anybody(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    email = random_email()
    response = request(
        session_scoped_client,
        "post",
        "/private/users/",
        body={
            "email": email,
            "password": random_lower_string(),
            "username": random_lower_string(),
        },
    )
    assert response.status_code == status.HTTP_200_OK
    created = session_scoped_session.exec(
        select(User).where(User.email == email),
    ).one()
    assert created.id == uuid.UUID(response.json()["id"])
