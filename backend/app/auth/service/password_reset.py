# TODO: Validate
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import HTTPException, status
from fastapi.responses import HTMLResponse
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session

from app.auth.constants import ALGORITHM
from app.config import settings
from app.schemas import Message
from app.users.schemas import UserUpdate
from app.users.service import accounts, lookup
from app.utils.service.email_delivery import send_email
from app.utils.service.email_templates import generate_reset_password_email


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
def password_reset_email(session: Session, email: str) -> Message:
    """Mail a password reset link, saying the same thing whoever the address is.

    An address the site has never seen reads exactly as one it has, since a
    difference between the two is what tells an attacker who has an account here.
    """
    user = lookup.get_user_by_email(session=session, email=email)
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
    user = lookup.get_user_by_email(session=session, email=email)
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
    accounts.update_user(
        session=session,
        db_user=user,
        user_in=UserUpdate(password=new_password),
    )
    return Message(message="Password updated successfully")


# TODO: Validate
def password_reset_email_response(session: Session, email: str) -> HTMLResponse:
    """Return the reset mail a `User` would be sent, as the page an admin reads."""
    user = lookup.get_user_by_email(session=session, email=email)
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
