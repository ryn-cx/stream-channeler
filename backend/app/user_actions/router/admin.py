# TODO: Validate
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import SessionDep, get_current_active_superuser
from app.schemas import ReadOptions
from app.user_actions.schemas import UserActionsPublic
from app.user_actions.service.listing import list_user_actions

router = APIRouter(
    prefix="/admin/user-actions",
    tags=["user-actions"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@router.get("")
def admin_get_user_actions(
    session: SessionDep,
    read_options: Annotated[ReadOptions, Query()],
) -> UserActionsPublic:
    return list_user_actions(session, read_options)
