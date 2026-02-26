# TODO: Validate
from typing import Annotated

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.auth.dependencies import SessionDep, get_current_user
from app.config import settings
from app.users.models import User

optional_oauth2 = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/login/access-token",
    auto_error=False,
)


def get_optional_user(
    session: SessionDep,
    token: str | None = Depends(optional_oauth2),
) -> User | None:
    if token is None:
        return None
    try:
        return get_current_user(session, token)
    except Exception:
        return None


OptionalUser = Annotated[User | None, Depends(get_optional_user)]
