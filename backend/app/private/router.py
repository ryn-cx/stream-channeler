from fastapi import APIRouter
from pydantic import BaseModel

from app.auth.dependencies import SessionDep
from app.auth.security import get_password_hash
from app.users.models import User
from app.users.schemas import UserPublic

router = APIRouter(tags=["private"], prefix="/private")


class PrivateUserCreate(BaseModel):
    email: str
    password: str
    username: str
    is_verified: bool = False


@router.post("/users/", response_model=UserPublic)
def create_user(user_in: PrivateUserCreate, session: SessionDep) -> User:
    """
    Create a new user.
    """

    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
    )

    session.add(user)
    session.commit()

    return user
