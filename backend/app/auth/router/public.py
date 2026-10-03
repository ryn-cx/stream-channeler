# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from app.auth.dependencies import SessionDep
from app.auth.schemas import NewPassword, Token
from app.auth.service import credentials, password_reset
from app.schemas import Message
from app.user_actions.dependencies import ActionLog
from app.user_actions.models import UserActionKind

router = APIRouter(tags=["login"])


# TODO: Validate
@router.post("/login/access-token")
def login_access_token(
    session: SessionDep,
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    action_log: ActionLog,
) -> Token:
    """OAuth2 compatible token login, get an access token for future requests."""
    try:
        return credentials.access_token_for_credentials(
            session,
            form_data.username,
            form_data.password,
        )
    except HTTPException:
        action_log.record(UserActionKind.login_failed, email=form_data.username)
        raise


# TODO: Validate
@router.post("/password-recovery/{email}")
def recover_password(email: str, session: SessionDep) -> Message:
    """Password Recovery."""
    return password_reset.password_reset_email(session, email)


# TODO: Validate
@router.post("/reset-password/")
def reset_password(session: SessionDep, body: NewPassword) -> Message:
    """Reset password."""
    return password_reset.reset_password_with_token(
        session,
        body.token,
        body.new_password,
    )
