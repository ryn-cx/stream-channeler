# TODO: Validate
from datetime import timedelta

from fastapi import HTTPException, status
from sqlmodel import Session

from app.auth.constants import DUMMY_HASH
from app.auth.schemas import Token
from app.auth.security import create_access_token, verify_password
from app.config import settings
from app.users.models import User
from app.users.service import lookup


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = lookup.get_user_by_email(session=session, email=email)
    if not db_user:
        # Prevent timing attacks by running password verification even when user doesn't exist
        # This ensures the response time is similar whether or not the email exists
        verify_password(password, DUMMY_HASH)
        return None
    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None
    if updated_password_hash:
        db_user.hashed_password = updated_password_hash
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
    return db_user


# TODO: Validate
def access_token_for_credentials(
    session: Session,
    email: str,
    password: str,
) -> Token:
    """Return an access token for the credentials, refusing anything else."""
    user = authenticate(session=session, email=email, password=password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    return Token(
        access_token=create_access_token(
            user.id,
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
        ),
    )
