# TODO: Validate


from fastapi import HTTPException, status
from sqlmodel import Session, col, delete, func, select

from app.channels.models import Channel
from app.config import settings
from app.schemas import Message
from app.users.models import User
from app.users.schemas import (
    UserCreate,
    UserPublic,
    UsersPublic,
    UserUpdate,
)
from app.users.service.accounts import (
    _reject_taken_email_or_username,
    create_user,
    update_user,
)
from app.users.service.lookup import get_user_by_email, get_user_by_username
from app.utils.service.email_delivery import send_email
from app.utils.service.email_templates import generate_new_account_email
from app.watches.models import Watch


# TODO: Validate
def list_users(session: Session, skip: int, limit: int) -> UsersPublic:
    """Read one page of every `User`, newest first."""
    count = session.exec(select(func.count()).select_from(User)).one()
    users = session.exec(
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit),
    ).all()
    return UsersPublic(
        data=[UserPublic.model_validate(user) for user in users],
        count=count,
    )


# TODO: Validate
def create_user_as_admin(session: Session, user_in: UserCreate) -> User:
    """Create a `User` on an admin's behalf and mail them their password."""
    if get_user_by_email(session=session, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system.",
        )
    if get_user_by_username(session=session, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system.",
        )
    user = create_user(session=session, user_create=user_in)
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
def update_user_as_admin(
    session: Session,
    db_user: User,
    user_in: UserUpdate,
) -> User:
    """Update any `User` on an admin's behalf."""
    _reject_taken_email_or_username(
        session,
        user_in.email,
        user_in.username,
        db_user.id,
    )
    return update_user(session=session, db_user=db_user, user_in=user_in)


# TODO: Validate
def delete_user_as_admin(session: Session, current_user: User, user: User) -> Message:
    """Delete a `User` and all of their media, which an admin may not do to themselves."""
    if user == current_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super users are not allowed to delete themselves",
        )
    session.exec(delete(Channel).where(col(Channel.user_id) == user.id))
    session.exec(delete(Watch).where(col(Watch.user_id) == user.id))
    session.delete(user)
    session.commit()
    return Message(message="User deleted successfully")
