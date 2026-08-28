# TODO: Validate
import uuid
from datetime import timedelta
from functools import cache

from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlmodel import Session

from app.auth.security import create_access_token, get_password_hash
from app.config import settings
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from tests.app.helpers.utils import random_email, random_lower_string

# Every test user answers to this password. Hashing is the single most expensive
# thing a test does - about 45ms a user - and nothing here depends on two users
# having different passwords, so the hash is computed once and shared.
TEST_PASSWORD = "test-password"  # noqa: S105 - Not a credential, the fixed password every test user has.


# TODO: Validate
@cache
def _shared_password_hash() -> str:
    return get_password_hash(TEST_PASSWORD)


# TODO: Validate
def create_random_user(session: Session, **kwargs: object) -> User:
    """Insert a `User` directly, skipping the password hash every signup pays.

    Going through `create_user` would hash a fresh password per user; every test
    user shares one hash instead, which is the difference between a test costing
    45ms and costing 1ms.
    """
    user = User(
        email=random_email(),
        username=random_lower_string(),
        hashed_password=_shared_password_hash(),
        **kwargs,  # type: ignore[arg-type]
    )
    session.add(user)
    session.flush()
    return user


# TODO: Validate
def create_random_superuser(session: Session, **kwargs: object) -> User:
    """Insert a `User` who may do anything."""
    return create_random_user(session, is_superuser=True, **kwargs)


# TODO: Validate
def auth_headers(user: User) -> dict[str, str]:
    """Return the `Authorization` header a signed-in `User` sends.

    Minted here rather than fetched from `/login/access-token`, which would spend
    a password verification (~45ms) to arrive at the same token.
    """
    token = create_access_token(user.id, expires_delta=timedelta(minutes=60))
    return {"Authorization": f"Bearer {token}"}


# TODO: Validate
def user_authentication_headers(
    *,
    client: TestClient,
    email: str,
    password: str,
) -> dict[str, str]:
    data = {"username": email, "password": password}
    r = client.post(f"{settings.API_V1_STR}/login/access-token", data=data)
    response = r.json()
    auth_token = response["access_token"]
    return {"Authorization": f"Bearer {auth_token}"}


# TODO: Validate
def authentication_token_from_email(
    *,
    client: TestClient,
    email: str,
    session: Session,
) -> dict[str, str]:
    password = random_lower_string()
    user = user_service.get_user_by_email(session=session, email=email)
    if not user:
        user_in_create = UserCreate(
            email=email,
            username=random_lower_string(),
            password=password,
        )
        user = user_service.create_user(session=session, user_create=user_in_create)
    else:
        user_in_update = UserUpdate(password=password)
        if not user.id:
            msg = "User id not set"
            raise ValueError(msg)
        user = user_service.update_user(
            session=session,
            db_user=user,
            user_in=user_in_update,
        )

    return user_authentication_headers(client=client, email=email, password=password)


# TODO: Validate
class CreatedUser(BaseModel):
    id: uuid.UUID
    email: str
    password: str
    headers: dict[str, str]


# TODO: Validate
def create_random_user_alt(client: TestClient, session: Session) -> CreatedUser:  # noqa: ARG001 - Kept so callers need not know a token is minted rather than fetched.
    user = create_random_user(session)
    return CreatedUser(
        id=user.id,
        email=user.email,
        password=TEST_PASSWORD,
        headers=auth_headers(user),
    )
