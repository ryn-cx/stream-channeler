import secrets

from sqlmodel import Session, func, select

from app.auth.security import get_password_hash
from app.users.constants import PLUGIN_USER_EMAIL
from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate


def get_or_create_plugin_user(*, session: Session) -> User:
    """Get or create the system user that owns official plugins."""
    user = get_user_by_email(session=session, email=PLUGIN_USER_EMAIL)
    if not user:
        user = create_user(
            session=session,
            user_create=UserCreate(
                email=PLUGIN_USER_EMAIL,
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
