# TODO: Validate
"""Tests that admin-media endpoints require superuser access."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.config import settings
from tests.users.utils import authentication_token_from_email, create_random_user

BASE_URL = f"{settings.API_V1_STR}/admin-media"

ENDPOINTS = [
    ("get", "/plugins"),
]


@pytest.fixture
def normal_user_headers(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> dict[str, str]:
    user = create_random_user(session_scoped_session)
    return authentication_token_from_email(
        client=session_scoped_client,
        email=user.email,
        session=session_scoped_session,
    )


class TestAdminMediaPermissions:
    @pytest.mark.parametrize(("method", "path"), ENDPOINTS)
    def test_superuser_can_access(
        self,
        session_scoped_client: TestClient,
        superuser_token_headers: dict[str, str],
        method: str,
        path: str,
    ) -> None:
        response = getattr(session_scoped_client, method)(
            f"{BASE_URL}{path}",
            headers=superuser_token_headers,
        )
        assert response.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize(("method", "path"), ENDPOINTS)
    def test_normal_user_forbidden(
        self,
        session_scoped_client: TestClient,
        normal_user_headers: dict[str, str],
        method: str,
        path: str,
    ) -> None:
        response = getattr(session_scoped_client, method)(
            f"{BASE_URL}{path}",
            headers=normal_user_headers,
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.parametrize(("method", "path"), ENDPOINTS)
    def test_unauthenticated_rejected(
        self,
        session_scoped_client: TestClient,
        method: str,
        path: str,
    ) -> None:
        response = getattr(session_scoped_client, method)(f"{BASE_URL}{path}")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
