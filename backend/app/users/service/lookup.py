# TODO: Validate


from sqlmodel import Session, func, select

from app.users.models import User

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
def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(func.lower(User.email) == func.lower(email))
    return session.exec(statement).first()


# TODO: Validate
def get_user_by_username(*, session: Session, username: str) -> User | None:
    statement = select(User).where(func.lower(User.username) == func.lower(username))
    return session.exec(statement).first()
