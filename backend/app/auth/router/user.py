# TODO: Validate


from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.users.schemas import UserPublic

router = APIRouter(tags=["login"])


# TODO: Validate
@router.post("/login/test-token", response_model=UserPublic)
def test_token(current_user: CurrentUser) -> CurrentUser:
    """Test access token."""
    return current_user
