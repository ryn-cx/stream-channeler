# TODO: Validate


import uuid

from fastapi import APIRouter

from app.auth.dependencies import (
    SessionDep,
)
from app.channels import service as channel_service
from app.channels.schemas import ChannelPublicListOutput
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import (
    UserPublic,
    UserRegister,
)

users_router = APIRouter(prefix="/users", tags=["users"])


# TODO: Validate
@users_router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> User:
    """Create new user without the need to be logged in."""
    return user_service.register_user(session, user_in)


# TODO: Validate
@users_router.get("/{user_id}/channels")
def get_user_public_channels(
    session: SessionDep,
    user_id: uuid.UUID,
) -> ChannelPublicListOutput:
    """List a `User`'s public, non-anonymous `Channel`s, highest score first."""
    return channel_service.public_channels_of_user(session, user_id)


router = APIRouter()


router.include_router(users_router)
