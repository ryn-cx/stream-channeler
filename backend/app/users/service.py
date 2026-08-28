# TODO: Validate


import secrets
import uuid
from collections.abc import Iterable

from fastapi import HTTPException, status
from sqlmodel import Session, col, delete, func, select

from app.auth.schemas import UpdatePassword
from app.auth.security import get_password_hash, verify_password
from app.channels.models import Channel
from app.config import settings
from app.episodes.user_urls import user_episode_url_count
from app.plugins.identifiers import CUSTOM_MEDIA_SOURCE_KEY
from app.schemas import Message
from app.sources.service import (
    OTHER_SOURCE_KEY,
    episode_counts_by_source_id,
    source_keys,
    sources_by_key,
)
from app.users.constants import PLUGIN_USER_EMAIL, PLUGIN_USER_USERNAME
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
from app.utils.service import generate_new_account_email, send_email
from app.watches.models import Watch

_SESSION_USERS = "users_by_email"


"""Where a session keeps the users it has already been asked for."""


# TODO: Validate
def _remembered_users(session: Session) -> dict[str, User]:
    """Return the users this session has answered with, by the address asked for.

    Kept on the session rather than read back out of its identity map, because
    that map holds its records weakly: a user nothing else is holding on to is
    dropped from it the moment Python collects it, and every plugin holds the
    plugin row rather than the user who owns it. What is remembered here is held
    strongly and let go when the session is.
    """
    remembered: dict[str, User] = session.info.setdefault(_SESSION_USERS, {})
    return remembered


# TODO: Validate
def get_user_in_session(*, session: Session, email: str) -> User | None:
    """Return the user `email` names if the session already holds them.

    Answered from what the session has been asked for before, and failing that
    from the records it is holding, so that a user read once is read once however
    many times it is asked for.
    """
    address = email.lower()
    remembered = _remembered_users(session).get(address)
    if remembered is not None and remembered in session:
        return remembered

    for instance in (*session.new, *session.identity_map.values()):
        if isinstance(instance, User) and instance.email.lower() == address:
            _remembered_users(session)[address] = instance
            return instance
    return None


# TODO: Validate
def get_or_create_plugin_user(*, session: Session) -> User:
    """Get or create the user that owns installed plugins."""
    user = get_user_in_session(session=session, email=PLUGIN_USER_EMAIL)
    if not user and not (
        user := get_user_by_email(session=session, email=PLUGIN_USER_EMAIL)
    ):
        user = create_user(
            session=session,
            user_create=UserCreate(
                email=PLUGIN_USER_EMAIL,
                username=PLUGIN_USER_USERNAME,
                password=secrets.token_urlsafe(32),
                is_superuser=False,
            ),
        )
    _remembered_users(session)[PLUGIN_USER_EMAIL.lower()] = user
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
def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == func.lower(email))
    return session.exec(statement).first()


# TODO: Validate
def get_user_by_username(*, session: Session, username: str) -> User | None:
    statement = select(User).where(func.lower(User.username) == func.lower(username))
    return session.exec(statement).first()


# TODO: Validate
def stored_preferences(
    rows: Iterable[UserSourcePreference],
) -> list[SourcePreference]:
    """Convert a user's stored preference rows into ordered `SourcePreference`s."""
    return [
        SourcePreference(source_key=row.source_key, enabled=row.enabled)
        for row in sorted(rows, key=lambda row: row.priority)
    ]


# TODO: Validate
def effective_source_preferences(
    session: Session,
    stored: list[SourcePreference],
) -> list[SourcePreference]:
    """Return the full ordered preference list (every stored source plus `Other`).

    The stored order and enabled flags win for keys that still exist; any source
    key the user has not stored is appended (enabled), and `Other` is guaranteed to
    be present as the final fallback. Unknown/stale keys are dropped.
    """
    stored_by_key = {preference.source_key: preference for preference in stored}
    default_order = [*source_keys(session), OTHER_SOURCE_KEY]
    valid_keys = set(default_order)

    ordered_keys: list[str] = []
    for preference in stored:
        source_key = preference.source_key
        if source_key in valid_keys and source_key not in ordered_keys:
            ordered_keys.append(source_key)
    for key in default_order:
        if key not in ordered_keys:
            ordered_keys.append(key)

    return [
        SourcePreference(
            source_key=key,
            enabled=stored_by_key[key].enabled if key in stored_by_key else True,
        )
        for key in ordered_keys
    ]


# TODO: Validate
def _source_preference_outputs(
    session: Session,
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


# TODO: Validate
def source_preferences_output(
    session: Session,
    current_user: User,
) -> list[SourcePreferenceOutput]:
    """Return every stored source plus `Other`, in the `User`'s priority order."""
    return _source_preference_outputs(
        session,
        current_user,
        effective_source_preferences(
            session,
            stored_preferences(current_user.source_preferences),
        ),
    )


# TODO: Validate
def replace_source_preferences(
    session: Session,
    current_user: User,
    preferences: list[SourcePreference],
) -> list[SourcePreferenceOutput]:
    """Replace a `User`'s source preferences (priority order plus enabled)."""
    allowed_keys = {*sources_by_key(session), OTHER_SOURCE_KEY}
    seen: set[str] = set()
    for preference in preferences:
        if preference.source_key not in allowed_keys:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unknown source {preference.source_key!r}.",
            )
        if preference.source_key in seen:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Duplicate source {preference.source_key!r}.",
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
    return source_preferences_output(session, current_user)


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
