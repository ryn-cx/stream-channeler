# TODO: Validate
import secrets
from collections.abc import Iterable

from sqlmodel import Session, func, select

from app.auth.security import get_password_hash
from app.sources.service import OTHER_SOURCE_KEY, source_keys
from app.users.constants import PLUGIN_USER_EMAIL, PLUGIN_USER_USERNAME
from app.users.models import User, UserSourcePreference
from app.users.schemas import SourcePreference, UserCreate, UserUpdate


def get_or_create_plugin_user(*, session: Session) -> User:
    """Get or create the user that owns installed plugins."""
    if not (user := get_user_by_email(session=session, email=PLUGIN_USER_EMAIL)):
        user = create_user(
            session=session,
            user_create=UserCreate(
                email=PLUGIN_USER_EMAIL,
                username=PLUGIN_USER_USERNAME,
                password=secrets.token_urlsafe(32),
                is_superuser=False,
            ),
        )
    return user


def create_user(*, session: Session, user_create: UserCreate) -> User:
    db_obj = User.model_validate(
        user_create,
        update={"hashed_password": get_password_hash(user_create.password)},
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


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


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == func.lower(email))
    return session.exec(statement).first()


def stored_preferences(
    rows: Iterable[UserSourcePreference],
) -> list[SourcePreference]:
    """Convert a user's stored preference rows into ordered `SourcePreference`s."""
    return [
        SourcePreference(source_key=row.source_key, enabled=row.enabled)
        for row in sorted(rows, key=lambda row: row.priority)
    ]


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
