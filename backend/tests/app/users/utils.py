# TODO: Validate
import uuid

from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlmodel import Session

from app.config import settings
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from tests.app.utils.utils import random_email, random_lower_string


# TODO: Validate
class CreatedUser(BaseModel):
    id: uuid.UUID
    email: str
    password: str
    headers: dict[str, str]


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
def create_random_user(db: Session) -> User:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    return user_service.create_user(session=db, user_create=user_in)


# TODO: Validate
def authentication_token_from_email(
    *,
    client: TestClient,
    email: str,
    db: Session,
) -> dict[str, str]:
    """
    Return a valid token for the user with given email.

    If the user doesn't exist it is created first.
    """
    password = random_lower_string()
    user = user_service.get_user_by_email(session=db, email=email)
    if not user:
        user_in_create = UserCreate(email=email, password=password)
        user = user_service.create_user(session=db, user_create=user_in_create)
    else:
        user_in_update = UserUpdate(password=password)
        if not user.id:
            msg = "User id not set"
            raise ValueError(msg)
        user = user_service.update_user(
            session=db,
            db_user=user,
            user_in=user_in_update,
        )

    return user_authentication_headers(client=client, email=email, password=password)


# TODO: Validate
def create_logged_in_user(client: TestClient, session: Session) -> CreatedUser:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(
        email=email,
        username=random_lower_string(),
        password=password,
    )
    user = user_service.create_user(session=session, user_create=user_in)
    headers = user_authentication_headers(
        client=client,
        email=email,
        password=password,
    )
    return CreatedUser(id=user.id, email=email, password=password, headers=headers)
