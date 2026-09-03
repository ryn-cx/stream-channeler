# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from app.auth import service as auth_service
from app.auth.dependencies import SessionDep
from app.auth.schemas import NewPassword, Token
from app.schemas import Message

router = APIRouter(tags=["login"])


# TODO: Validate
@router.post("/login/access-token")
def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
) -> Token:
    """OAuth2 compatible token login, get an access token for future requests."""
    return auth_service.access_token_for_credentials(
        session,
        form_data.username,
        form_data.password,
    )


# TODO: Validate
@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """Password Recovery."""
    return auth_service.password_reset_email(session, email)


# TODO: Validate
@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """Reset password."""
    return auth_service.reset_password_with_token(
        session,
        body.token,
        body.new_password,
    )
