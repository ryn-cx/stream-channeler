# TODO: Validate
import uuid
from random import shuffle
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import col, delete, func, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.auth.schemas import UpdatePassword
from app.auth.security import get_password_hash, verify_password
from app.channels import service as channel_service
from app.channels.models import Channel
from app.channels.schemas import ChannelListOutput, ChannelPublicListOutput
from app.config import settings
from app.episodes.user_urls import user_episode_url_count
from app.models import Visibility
from app.plugins.identifiers import CUSTOM_MEDIA_SOURCE_KEY
from app.schemas import Message
from app.sources.service import (
    OTHER_SOURCE_KEY,
    episode_counts_by_source_id,
    sources_by_key,
)
from app.users import service as user_service
from app.users.dependencies import ExistingUser
from app.users.models import User, UserSourcePreference
from app.users.schemas import (
    SourcePreference,
    SourcePreferenceOutput,
    UserCreate,
    UserPublic,
    UserRegister,
    UsersPublic,
    UserUpdate,
    UserUpdateMe,
)
from app.utils import service as email_service
from app.watches.models import Watch

users_router = APIRouter(prefix="/users", tags=["users"])
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
        email_data = email_service.generate_new_account_email(
            email_to=user_in.email,
            username=user_in.email,
            password=user_in.password,
        )
        email_service.send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


# TODO: Validate
@users_router.patch("/me", response_model=UserPublic)
def update_user_me(
    *,
    session: SessionDep,
    user_in: UserUpdateMe,
    current_user: CurrentUser,
) -> User:
    """Update own user."""
    if user_in.email:
        existing_user = user_service.get_user_by_email(
            session=session,
            email=user_in.email,
        )
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )
    if user_in.username:
        existing_user = user_service.get_user_by_username(
            session=session,
            username=user_in.username,
        )
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this username already exists",
            )
    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


# TODO: Validate
@users_router.patch("/me/password")
def update_password_me(
    *,
    session: SessionDep,
    body: UpdatePassword,
    current_user: CurrentUser,
) -> Message:
    """Update own password."""
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
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
    return Message(message="Password updated successfully")


# TODO: Validate
def _source_preference_outputs(
    session: SessionDep,
    current_user: User,
    preferences: list[SourcePreference],
) -> list[SourcePreferenceOutput]:
    """Attach each source's stored display name, favicon and episode count."""
    sources = sources_by_key(session)
    counts = episode_counts_by_source_id(session)
    installed_ids = {source.id for source in sources.values()}
    other_count = sum(
        count for source_id, count in counts.items() if source_id not in installed_ids
    )
    custom_media_count = user_episode_url_count(session, current_user)
    outputs: list[SourcePreferenceOutput] = []
    for preference in preferences:
        source = sources.get(preference.source_key)
        if preference.source_key == OTHER_SOURCE_KEY:
            episode_count = other_count
        elif preference.source_key == CUSTOM_MEDIA_SOURCE_KEY:
            episode_count = custom_media_count
        else:
            episode_count = counts.get(source.id, 0) if source else 0
        outputs.append(
            SourcePreferenceOutput(
                source_key=preference.source_key,
                enabled=preference.enabled,
                name=source.name if source else None,
                favicon_url=source.favicon_url if source else None,
                episode_count=episode_count,
            ),
        )
    return outputs


# TODO: Validate
@users_router.get("/me/source-preferences")
def read_source_preferences(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[SourcePreferenceOutput]:
    """Get the current user's source priority and enable/disable preferences.

    Always returns every stored source plus `Other`, in priority order.
    """
    return _source_preference_outputs(
        session,
        current_user,
        user_service.effective_source_preferences(
            session,
            user_service.stored_preferences(current_user.source_preferences),
        ),
    )


# TODO: Validate
@users_router.put("/me/source-preferences")
def update_source_preferences(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    preferences: list[SourcePreference],
) -> list[SourcePreferenceOutput]:
    """Replace the current user's source preferences (priority order + enabled)."""
    allowed_keys = {*sources_by_key(session), OTHER_SOURCE_KEY}
    seen: set[str] = set()
    for preference in preferences:
        if preference.source_key not in allowed_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown source '{preference.source_key}'.",
            )
        if preference.source_key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate source '{preference.source_key}'.",
            )
        seen.add(preference.source_key)

    for existing in list(current_user.source_preferences):
        session.delete(existing)
    session.flush()
    for index, preference in enumerate(preferences):
        session.add(
            UserSourcePreference(
                user_id=current_user.id,
                source_key=preference.source_key,
                priority=index,
                enabled=preference.enabled,
            ),
        )
    session.commit()
    session.refresh(current_user)
    return _source_preference_outputs(
        session,
        current_user,
        user_service.effective_source_preferences(
            session,
            user_service.stored_preferences(current_user.source_preferences),
        ),
    )


# TODO: Validate
@users_router.get("/me", response_model=UserPublic)
def read_user_me(current_user: CurrentUser) -> CurrentUser:
    """Get current user."""
    return current_user


# TODO: Validate
@users_router.delete("/me")
def delete_user_me(session: SessionDep, current_user: CurrentUser) -> Message:
    """Delete own user."""
    if current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super users are not allowed to delete themselves",
        )
    session.delete(current_user)
    session.commit()
    return Message(message="User deleted successfully")


# TODO: Validate
@users_router.post("/signup", response_model=UserPublic)
def register_user(session: SessionDep, user_in: UserRegister) -> User:
    """Create new user without the need to be logged in."""
    user = user_service.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this email already exists in the system",
        )
    user = user_service.get_user_by_username(session=session, username=user_in.username)
    if user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The user with this username already exists in the system",
        )
    user_create = UserCreate.model_validate(user_in)
    return user_service.create_user(session=session, user_create=user_create)


# TODO: Validate
@users_router.get("/{user_id}", response_model=UserPublic)
def read_user_by_id(
    user_id: uuid.UUID,
    session: SessionDep,
    current_user: CurrentUser,
) -> User | None:
    """Get a specific user by id."""
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


# TODO: Validate
@users_router.get("/{user_id}/channels")
def get_user_public_channels(
    session: SessionDep,
    user_id: uuid.UUID,
) -> ChannelPublicListOutput:
    """List a `User`'s public, non-anonymous `Channel`s, highest score first."""
    rows = session.exec(
        select(Channel, User.username)
        .join(User, col(User.id) == Channel.user_id)
        .where(
            Channel.user_id == user_id,
            Channel.visibility == Visibility.public,
            col(Channel.anonymous).is_(False),
        ),
    ).all()
    favorite_counts = channel_service.channel_favorite_counts(
        session,
        [channel.id for channel, _username in rows],
    )
    data = [
        channel_service.public_channel_output(
            channel,
            username,
            favorite_counts.get(channel.id, 0),
        )
        for channel, username in rows
    ]
    shuffle(data)
    data.sort(key=lambda channel: channel.favorite_count, reverse=True)
    return ChannelPublicListOutput(data=data, count=len(data))


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
router.include_router(users_router)
router.include_router(admin_router)
