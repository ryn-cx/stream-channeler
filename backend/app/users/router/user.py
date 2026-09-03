# TODO: Validate


import uuid

from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.auth.schemas import UpdatePassword
from app.schemas import Message
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import (
    SourcePreference,
    SourcePreferenceOutput,
    UserPublic,
    UserUpdateMe,
)

users_router = APIRouter(prefix="/users", tags=["users"])


# TODO: Validate
@users_router.patch("/me", response_model=UserPublic)
def update_user_me(
    *,
    session: SessionDep,
    user_in: UserUpdateMe,
    current_user: CurrentUser,
) -> User:
    """Update own user."""
    return user_service.update_own_user(session, current_user, user_in)


# TODO: Validate
@users_router.patch("/me/password")
def update_password_me(
    *,
    session: SessionDep,
    body: UpdatePassword,
    current_user: CurrentUser,
) -> Message:
    """Update own password."""
    return user_service.change_own_password(session, current_user, body)


# TODO: Validate
@users_router.get("/me/source-preferences")
def read_source_preferences(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[SourcePreferenceOutput]:
    """Get the current user's source priority and enable/disable preferences.

    Always returns every stored source plus `Other`, in priority order.
    """
    return user_service.source_preferences_output(session, current_user)


# TODO: Validate
@users_router.put("/me/source-preferences")
def update_source_preferences(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    preferences: list[SourcePreference],
) -> list[SourcePreferenceOutput]:
    """Replace the current user's source preferences (priority order + enabled)."""
    return user_service.replace_source_preferences(session, current_user, preferences)


# TODO: Validate
@users_router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> CurrentUser:
    """Get current user."""
    return current_user


# TODO: Validate
@users_router.delete("/me")
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Message:
    """Delete own user."""
    return user_service.delete_own_user(session, current_user)


# TODO: Validate
@users_router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> User | None:
    """Get a specific user by id."""
    return user_service.readable_user(session, current_user, user_id)


router = APIRouter()


router.include_router(users_router)
