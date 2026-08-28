# TODO: Validate


import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.channels import service as channel_service
from app.channels.schemas import ChannelListOutput
from app.schemas import Message
from app.users import service as user_service
from app.users.dependencies import ExistingUser
from app.users.models import User
from app.users.schemas import (
    UserCreate,
    UserPublic,
    UsersPublic,
    UserUpdate,
)

admin_router = APIRouter(
    prefix="/admin/users",
    tags=["users"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@admin_router.get("")
def read_users(
    session: SessionDep,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1)] = 100_000,
) -> UsersPublic:
    """Retrieve users."""
    return user_service.list_users(session, skip, limit)


# TODO: Validate
@admin_router.post("", response_model=UserPublic)
def create_user(*, session: SessionDep, user_in: UserCreate) -> User:
    """Create new user."""
    return user_service.create_user_as_admin(session, user_in)


# TODO: Validate
@admin_router.get("/{user_id}/channels")
def admin_list_user_channels(
    session: SessionDep,
    user_id: uuid.UUID,
) -> list[ChannelListOutput]:
    """List every `Channel` editable by a single `User`."""
    return channel_service.channels_of_user(session, user_id)


# TODO: Validate
@admin_router.patch(
    "/{user_id}",  # noqa: FAST003 - Used by ExistingUser.
    response_model=UserPublic,
)
def update_user(
    *,
    session: SessionDep,
    db_user: ExistingUser,
    user_in: UserUpdate,
) -> User | None:
    """Update a user."""
    return user_service.update_user_as_admin(session, db_user, user_in)


# TODO: Validate
@admin_router.delete("/{user_id}")  # noqa: FAST003 - Used by ExistingUser.
def delete_user(
    session: SessionDep,
    current_user: SuperUser,
    user: ExistingUser,
) -> Message:
    """Delete a user."""
    return user_service.delete_user_as_admin(session, current_user, user)


router = APIRouter()
router.include_router(admin_router)
