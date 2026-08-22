# TODO: Validate
import secrets
from collections.abc import Iterable

from sqlmodel import Session, func, select

from app.auth.security import get_password_hash
from app.sources.service import OTHER_SOURCE_KEY, source_keys
from app.users.constants import PLUGIN_USER_EMAIL, PLUGIN_USER_USERNAME
from app.users.models import User, UserSourcePreference
from app.users.schemas import SourcePreference, UserCreate, UserUpdate

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
