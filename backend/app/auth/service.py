from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from app.auth.constants import ALGORITHM, DUMMY_HASH
from app.auth.schemas import Token
from app.auth.security import create_access_token, verify_password
from app.config import settings
from app.schemas import Message
from app.users import service as user_service
from app.users.models import User
from app.users.schemas import UserUpdate
from app.utils.service import generate_reset_password_email, send_email


def authenticate(*, session: Session, email: str, password: str) -> User | None:
    db_user = user_service.get_user_by_email(session=session, email=email)
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


def generate_password_reset_token(email: str) -> str:
    delta = timedelta(hours=settings.EMAIL_RESET_TOKEN_EXPIRE_HOURS)
    now = datetime.now(UTC)
    expires = now + delta
    exp = expires.timestamp()
    return jwt.encode(
        {"exp": exp, "nbf": now, "sub": email},
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )


def verify_password_reset_token(token: str) -> str | None:
    try:
        decoded_token = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return str(decoded_token["sub"])
    except InvalidTokenError:
        return None


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


# TODO: Validate
def password_reset_email(session: Session, email: str) -> Message:
    """Mail a password reset link, saying the same thing whoever the address is.

    An address the site has never seen reads exactly as one it has, since a
    difference between the two is what tells an attacker who has an account here.
    """
    user = user_service.get_user_by_email(session=session, email=email)
    if user:
        email_data = generate_reset_password_email(
            email_to=user.email,
            email=email,
            token=generate_password_reset_token(email=email),
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link",
    )


# TODO: Validate
def reset_password_with_token(
    session: Session,
    token: str,
    new_password: str,
) -> Message:
    """Set a `User`'s password from a reset token."""
    email = verify_password_reset_token(token=token)
    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
    user = user_service.get_user_by_email(session=session, email=email)
    if not user:
        # A token naming somebody who is gone is answered as an invalid token, so
        # a caller cannot read who still has an account out of the difference.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid token",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user",
        )
    user_service.update_user(
        session=session,
        db_user=user,
        user_in=UserUpdate(password=new_password),
    )
    return Message(message="Password updated successfully")


# TODO: Validate
def password_reset_email_response(session: Session, email: str) -> HTMLResponse:
    """Return the reset mail a `User` would be sent, as the page an admin reads."""
    user = user_service.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="The user with this username does not exist in the system.",
        )
    email_data = generate_reset_password_email(
        email_to=user.email,
        email=email,
        token=generate_password_reset_token(email=email),
    )
    return HTMLResponse(
        content=email_data.html_content,
        headers={"subject:": email_data.subject},
    )
