# TODO: Validate

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any

from fastapi import HTTPException, Path
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, col, select
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.dependencies import CurrentUser, SessionDep
from app.media.schemas import MediaReadOptions, MediaScope
from app.models import Visibility
from app.plugins.models import Plugin
from app.schemas import USER_OWNED_MODELS, Message
from app.service import list_response
from app.users.dependencies import OptionalUser
from app.users.models import User
from app.users.service import get_or_create_plugin_user


# TODO: Validate
def readable_record[T: USER_OWNED_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if readable by the user."""

    # TODO: Validate
    def dependency(
        session: SessionDep,
        optional_user: OptionalUser,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if result := session.exec(select(model).where(model.id == record_id)).first():
            if result.is_publically_readable(session):
                return result
            if optional_user is None:
                raise HTTPException(status_code=401, detail="Not authenticated")
            record_user_id = result.owner_id(session)
            if optional_user.is_superuser or optional_user.id == record_user_id:
                return result
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to access this {model.__name__}",
            )
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


# TODO: Validate
def editable_record[T: USER_OWNED_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if owned by the user."""

    # TODO: Validate
    def dependency(
        session: SessionDep,
        current_user: CurrentUser,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if record := session.exec(select(model).where(model.id == record_id)).first():
            record_user_id = record.owner_id(session)
            if current_user.is_superuser or current_user.id == record_user_id:
                return record
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to access this {model.__name__}",
            )
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


# TODO: Validate
def existing_record[T: USER_OWNED_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if it exists.

    Unlike `owned_record`/`readable_record` this performs no authorization check, so
    routes using it must guard access separately (e.g. `get_current_active_superuser`).
    """

    # TODO: Validate
    def dependency(
        session: SessionDep,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if record := session.exec(select(model).where(model.id == record_id)).first():
            return record
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


# TODO: Validate
def delete_record(
    session: Session,
    existing_record: USER_OWNED_MODELS,
) -> Message:
    """Delete the record and return a success message."""
    session.delete(existing_record)
    session.commit()
    return Message(message=f"{type(existing_record).__name__} deleted successfully")


# TODO: Validate
def media_scoped_list_response[ResponseT: BaseModel](  # noqa: PLR0913
    *,
    session: Session,
    base: SelectOfScalar[Any],
    response_model: type[ResponseT],
    schema: type[SQLModel],
    read_options: MediaReadOptions,
    current_user: User,
    default_sort: datetime | None = None,
    tiebreaker: uuid.UUID | None = None,
    extra_columns: dict[str, Any] | None = None,
) -> ResponseT:
    """List media for the requested scope, applying that scope's access rules.

    Media carries no owner or visibility of its own, so every scope filters on the
    owning `Plugin` and its `User`, both of which `base` already joins. `owned` and
    `public` are open to any `User`; `all`, `official` and `others` are admin-only.
    """
    scope = read_options.scope
    if scope == MediaScope.owned:
        base = base.where(User.id == current_user.id)
    elif scope == MediaScope.public:
        base = base.where(Plugin.visibility == Visibility.public)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        plugin_user = get_or_create_plugin_user(session=session)
        if scope == MediaScope.official:
            base = base.where(User.id == plugin_user.id)
        elif scope == MediaScope.others:
            base = base.where(
                col(User.id).not_in([current_user.id, plugin_user.id]),
            )
        # `all` deliberately adds no filter, so it includes official media.
    return list_response(
        session=session,
        base=base,
        response_model=response_model,
        schema=schema,
        params=read_options,
        current_user=current_user,
        default_sort=default_sort,
        tiebreaker=tiebreaker,
        extra_columns=extra_columns,
    )
