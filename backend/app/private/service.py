# TODO: Validate
from sqlmodel import Session

from app.auth.security import get_password_hash
from app.private.schemas import PrivateUserCreate
from app.users.models import User


# TODO: Validate
def create_user(session: Session, user_in: PrivateUserCreate) -> User:
    """Create a `User` from the private endpoint, with no checks of any kind."""
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
    )
    session.add(user)
    session.commit()
    return user
