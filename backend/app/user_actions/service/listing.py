# TODO: Validate
from typing import Any

from sqlalchemy import String, cast
from sqlmodel import Session, col, func, select

from app.schemas import ReadOptions
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.user_actions.models import UserAction
from app.user_actions.schemas import UserActionOutput, UserActionsPublic
from app.users.models import User


# TODO: Validate
def list_user_actions(session: Session, params: ReadOptions) -> UserActionsPublic:
    columns: dict[str, Any] = {
        "created_at": col(UserAction.created_at),
        "action": col(UserAction.action),
        "ip_address": col(UserAction.ip_address),
        "username": col(User.username),
        "email": col(User.email),
        "details": cast(col(UserAction.details), String),
    }
    base: Any = select(
        UserAction,
        col(User.username),
        col(User.email),
    ).outerjoin(User, onclause=col(UserAction.user_id) == col(User.id))
    filtered = _apply_filter_options(base, params.filter_options, columns)
    total_count = session.exec(
        select(func.count()).select_from(UserAction),
    ).one()
    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            params.sort_options,
            columns,
            [col(UserAction.created_at).desc()],
            col(UserAction.id),  # type: ignore[arg-type]
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return UserActionsPublic(
        data=[
            UserActionOutput(
                id=action.id,
                created_at=action.created_at,
                action=action.action,
                ip_address=action.ip_address,
                user_id=action.user_id,
                username=username,
                email=email,
                details=action.details,
            )
            for action, username, email in session.exec(page).all()
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=True,
    )
