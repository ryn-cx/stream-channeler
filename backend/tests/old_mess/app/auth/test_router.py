# TODO: Validate
from unittest.mock import patch

from fastapi import status
from fastapi.testclient import TestClient
from pwdlib.hashers.bcrypt import BcryptHasher
from sqlmodel import Session

from app.auth.security import get_password_hash, verify_password
from app.auth.service import generate_password_reset_token
from app.config import settings
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserCreate
from tests.old_mess.app.users.utils import user_authentication_headers
from tests.old_mess.app.utils.utils import random_email, random_lower_string


# TODO: Validate
def test_get_access_token(session_scoped_client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": settings.FIRST_SUPERUSER_PASSWORD,
    }
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data=login_data,
    )
    tokens = r.json()
    assert r.status_code == status.HTTP_200_OK
    assert "access_token" in tokens
    assert tokens["access_token"]


# TODO: Validate
def test_get_access_token_incorrect_password(session_scoped_client: TestClient) -> None:
    login_data = {
        "username": settings.FIRST_SUPERUSER,
        "password": "incorrect",
    }
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data=login_data,
    )
    assert r.status_code == status.HTTP_400_BAD_REQUEST


# TODO: Validate
def test_use_access_token(
    session_scoped_client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/login/test-token",
        headers=superuser_token_headers,
    )
    result = r.json()
    assert r.status_code == status.HTTP_200_OK
    assert "email" in result


# TODO: Validate
def test_recovery_password(
    session_scoped_client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    with (
        patch("app.config.settings.SMTP_HOST", "smtp.example.com"),
        patch("app.config.settings.SMTP_USER", "admin@example.com"),
    ):
        email = "test@example.com"
        r = session_scoped_client.post(
            f"{settings.API_V1_STR}/password-recovery/{email}",
            headers=normal_user_token_headers,
        )
        assert r.status_code == status.HTTP_200_OK
        assert r.json() == {
            "message": "If that email is registered, we sent a password recovery link",
        }


# TODO: Validate
def test_recovery_password_user_not_exits(
    session_scoped_client: TestClient,
    normal_user_token_headers: dict[str, str],
) -> None:
    email = "jVgQr@example.com"
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/password-recovery/{email}",
        headers=normal_user_token_headers,
    )
    # Should return 200 with generic message to prevent email enumeration attacks
    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {
        "message": "If that email is registered, we sent a password recovery link",
    }


# TODO: Validate
def test_reset_password(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    email = random_email()
    password = random_lower_string()
    new_password = random_lower_string()

    user_create = UserCreate(
        email=email,
        username="Test User",
        password=password,
        is_active=True,
        is_superuser=False,
    )
    user = user_service.create_user(
        session=session_scoped_session,
        user_create=user_create,
    )
    token = generate_password_reset_token(email=email)
    headers = user_authentication_headers(
        client=session_scoped_client,
        email=email,
        password=password,
    )
    data = {"new_password": new_password, "token": token}

    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=headers,
        json=data,
    )

    assert r.status_code == status.HTTP_200_OK
    assert r.json() == {"message": "Password updated successfully"}

    session_scoped_session.refresh(user)
    verified, _ = verify_password(new_password, user.hashed_password)
    assert verified


# TODO: Validate
def test_reset_password_invalid_token(
    session_scoped_client: TestClient,
    superuser_token_headers: dict[str, str],
) -> None:
    data = {"new_password": "changethis", "token": "invalid"}
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/reset-password/",
        headers=superuser_token_headers,
        json=data,
    )
    response = r.json()

    assert "detail" in response
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert response["detail"] == "Invalid token"


# TODO: Validate
def test_login_with_bcrypt_password_upgrades_to_argon2(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    """Test that logging in with a bcrypt password hash upgrades it to argon2."""
    email = random_email()
    password = random_lower_string()

    # Create a bcrypt hash directly (simulating legacy password)
    bcrypt_hasher = BcryptHasher()
    bcrypt_hash = bcrypt_hasher.hash(password)
    assert bcrypt_hash.startswith("$2")  # bcrypt hashes start with $2

    user = User(
        email=email,
        username=random_lower_string(),
        hashed_password=bcrypt_hash,
        is_active=True,
    )
    session_scoped_session.add(user)
    session_scoped_session.commit()
    session_scoped_session.refresh(user)

    assert user.hashed_password.startswith("$2")

    login_data = {"username": email, "password": password}
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data=login_data,
    )
    assert r.status_code == status.HTTP_200_OK
    tokens = r.json()
    assert "access_token" in tokens

    session_scoped_session.refresh(user)

    # Verify the hash was upgraded to argon2
    assert user.hashed_password.startswith("$argon2")

    verified, updated_hash = verify_password(password, user.hashed_password)
    assert verified
    # Should not need another update since it's already argon2
    assert updated_hash is None


# TODO: Validate
def test_login_with_argon2_password_keeps_hash(
    session_scoped_client: TestClient,
    session_scoped_session: Session,
) -> None:
    """Test that logging in with an argon2 password hash does not update it."""
    email = random_email()
    password = random_lower_string()

    # Create an argon2 hash (current default)
    argon2_hash = get_password_hash(password)
    assert argon2_hash.startswith("$argon2")

    # Create user with argon2 hash
    user = User(
        email=email,
        username=random_lower_string(),
        hashed_password=argon2_hash,
        is_active=True,
    )
    session_scoped_session.add(user)
    session_scoped_session.commit()
    session_scoped_session.refresh(user)

    original_hash = user.hashed_password

    login_data = {"username": email, "password": password}
    r = session_scoped_client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data=login_data,
    )
    assert r.status_code == status.HTTP_200_OK
    tokens = r.json()
    assert "access_token" in tokens

    session_scoped_session.refresh(user)

    assert user.hashed_password == original_hash
    assert user.hashed_password.startswith("$argon2")
