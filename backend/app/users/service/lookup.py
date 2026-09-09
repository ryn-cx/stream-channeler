# TODO: Validate


from sqlmodel import Session, func, select

from app.users.models import User


# TODO: Validate
def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == func.lower(email))
    return session.exec(statement).first()


# TODO: Validate
def get_user_by_username(*, session: Session, username: str) -> User | None:
    statement = select(User).where(func.lower(User.username) == func.lower(username))
    return session.exec(statement).first()
