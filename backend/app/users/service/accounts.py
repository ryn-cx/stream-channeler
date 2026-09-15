# TODO: Validate


import secrets
import uuid

from fastapi import HTTPException, status
from sqlmodel import Session

from app.auth.schemas import UpdatePassword
from app.auth.security import get_password_hash, verify_password
from app.schemas import Message
from app.users.models import User
from app.users.schemas import (
    UserCreate,
    UserRegister,
    UserUpdate,
    UserUpdateMe,
)
from app.users.service.lookup import get_user_by_email, get_user_by_username


# TODO: Validate
def get_or_create_automatic_channel_user(session: Session, plugin_name: str) -> User:
    user = get_user_by_email(session=session, email=plugin_name)
    if not user:
        if get_user_by_username(session=session, username=plugin_name):
            msg = f"Username {plugin_name} is already taken by another user"
            raise ValueError(msg)
        user = User(
            email=plugin_name,
            username=plugin_name,
            is_superuser=False,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
        )
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


# TODO: Validate
def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create,
        update={"hashed_password": get_password_hash(user_create.password)},
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


# TODO: Validate
def update_user(*, session: Session, db_user: User, user_in: UserUpdate) -> User:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data: dict[str, str] = {}
    if "password" in user_data:
        password = user_data["password"]
        hashed_password = get_password_hash(password)
        extra_data["hashed_password"] = hashed_password
    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


# TODO: Validate
def _reject_taken_email_or_username(
    session: Session,
    email: str | None,
    username: str | None,
    user_id: uuid.UUID | None = None,
) -> None:
    """Refuse an address or name another `User` already answers to."""
    if email:
        existing = get_user_by_email(session=session, email=email)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )
    if username:
        existing = get_user_by_username(session=session, username=username)
        if existing and existing.id != user_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this username already exists",
            )


# TODO: Validate
def register_user(session: Session, user_in: UserRegister) -> User:
    """Create a `User` from a signup, refusing an address or name already taken."""
    if get_user_by_email(session=session, email=user_in.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        )
    if get_user_by_username(session=session, username=user_in.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system",
        )
    return create_user(
        session=session,
        user_create=UserCreate.model_validate(user_in),
    )


# TODO: Validate
def update_own_user(
    session: Session,
    current_user: User,
    user_in: UserUpdateMe,
) -> User:
    """Update the fields a `User` may set on themselves."""
    _reject_taken_email_or_username(
        session,
        user_in.email,
        user_in.username,
        current_user.id,
    )
    current_user.sqlmodel_update(user_in.model_dump(exclude_unset=True))
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


# TODO: Validate
def change_own_password(
    session: Session,
    current_user: User,
    body: UpdatePassword,
) -> Message:
    """Replace a `User`'s password once they have proved they know the old one."""
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect password",
        )
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as the current one",
        )
    current_user.hashed_password = get_password_hash(body.new_password)
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


# TODO: Validate
def delete_own_user(session: Session, current_user: User) -> Message:
    """Delete the `User` making the request, which a superuser may not do."""
    if current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super users are not allowed to delete themselves",
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


# TODO: Validate
def readable_user(
    session: Session,
    current_user: User,
    user_id: uuid.UUID,
) -> User | None:
    """Return the `User` an id names, which only they and an admin may read."""
    user = session.get(User, user_id)
    if user == current_user:
        return user
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user
