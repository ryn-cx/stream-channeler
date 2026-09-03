# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import SessionDep
from app.private import service
from app.private.schemas import PrivateUserCreate
from app.users.models import User
from app.users.schemas import UserPublic

router = APIRouter(tags=["private"], prefix="/private")


# TODO: Validate
@router.post("/users/", response_model=UserPublic)
def create_user(user_in: PrivateUserCreate, session: SessionDep) -> User:
    """Create a new user."""
    return service.create_user(session, user_in)
