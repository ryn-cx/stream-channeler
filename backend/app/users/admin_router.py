# TODO: Validate


import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import col, delete, func, select

from app.auth.dependencies import (
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.channels import service as channel_service
from app.channels.models import Channel
from app.channels.schemas import ChannelListOutput
from app.config import settings
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
from app.utils.service import generate_new_account_email, send_email
from app.watches.models import Watch

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
    count_statement = select(func.count()).select_from(User)
    count = session.exec(count_statement).one()

    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    users = session.exec(statement).all()

    users_public = [UserPublic.model_validate(user) for user in users]
    return UsersPublic(data=users_public, count=count)


# TODO: Validate
@admin_router.post("", response_model=UserPublic)
def create_user(*, session: SessionDep, user_in: UserCreate) -> User:
    """Create new user."""
    user = user_service.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )

    user = user_service.get_user_by_username(session=session, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system.",
        )

    user = user_service.create_user(session=session, user_create=user_in)
    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email,
            username=user_in.email,
            password=user_in.password,
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


# TODO: Validate
@admin_router.get("/{user_id}/channels")
def admin_list_user_channels(
    session: SessionDep,
    user_id: uuid.UUID,
) -> list[ChannelListOutput]:
    """List every `Channel` editable by a single `User`."""
    rows = session.exec(
        select(Channel, User.username)
        .join(User, col(User.id) == Channel.user_id)
        .where(Channel.user_id == user_id),
    ).all()
    favorite_counts = channel_service.channel_favorite_counts(
        session,
        [channel.id for channel, _username in rows],
    )
    return [
        ChannelListOutput.model_validate(
            channel,
            update={
                "username": username,
                "favorite_count": favorite_counts.get(channel.id, 0),
            },
        )
        for channel, username in rows
    ]


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
    if user_in.email:
        existing_user = user_service.get_user_by_email(
            session=session,
            email=user_in.email,
        )
        if existing_user and existing_user.id != db_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

    if user_in.username:
        existing_user = user_service.get_user_by_username(
            session=session,
            username=user_in.username,
        )
        if existing_user and existing_user.id != db_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this username already exists",
            )

    return user_service.update_user(
        session=session,
        db_user=db_user,
        user_in=user_in,
    )


# TODO: Validate
@admin_router.delete("/{user_id}")  # noqa: FAST003 - Used by ExistingUser.
def delete_user(
    session: SessionDep,
    current_user: SuperUser,
    user: ExistingUser,
) -> Message:
    """Delete a user."""
    if user == current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super users are not allowed to delete themselves",
        )
    statement = delete(Channel).where(col(Channel.user_id) == user.id)
    session.exec(statement)
    statement = delete(Watch).where(col(Watch.user_id) == user.id)
    session.exec(statement)
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")


router = APIRouter()
router.include_router(admin_router)
