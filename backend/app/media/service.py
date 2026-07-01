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
from app.media.schemas import MediaOwner, MediaReadOptions
from app.plugins.models import Plugin
from app.schemas import MEDIA_MODELS, Message, ReadOptions
from app.service import get_read_results
from app.users.dependencies import OptionalUser
from app.users.models import User
from app.users.service import get_or_create_plugin_user


def readable_record[T: MEDIA_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if readable by the user."""

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


def editable_record[T: MEDIA_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if owned by the user."""

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


def existing_record[T: MEDIA_MODELS](
    model: type[T],
    path_name: str,
) -> Callable[..., T]:
    """Build a FastAPI dependency that returns the record if it exists.

    Unlike `owned_record`/`readable_record` this performs no authorization check, so
    routes using it must guard access separately (e.g. `get_current_active_superuser`).
    """

    def dependency(
        session: SessionDep,
        record_id: Annotated[uuid.UUID, Path(alias=path_name)],
    ) -> T:
        if record := session.exec(select(model).where(model.id == record_id)).first():
            return record
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


def delete_record(
    session: Session,
    existing_record: MEDIA_MODELS,
) -> Message:
    """Delete the record and return a success message."""
    session.delete(existing_record)
    session.commit()
    return Message(message=f"{type(existing_record).__name__} deleted successfully")


def filter_media_by_owner[T](
    base: SelectOfScalar[T],
    *,
    owner: MediaOwner,
    current_user: User,
    session: Session,
) -> SelectOfScalar[T]:
    plugin_user = get_or_create_plugin_user(session=session)
    if owner == MediaOwner.official:
        return base.where(Plugin.user_id == plugin_user.id)
    return base.where(col(Plugin.user_id).not_in([current_user.id, plugin_user.id]))


def media_list_response[ResponseT: BaseModel](  # noqa: PLR0913
    *,
    session: Session,
    base: SelectOfScalar[Any],
    response_model: type[ResponseT],
    schema: type[SQLModel],
    params: ReadOptions,
    current_user: User | None,
    default_sort: datetime | None = None,
    tiebreaker: uuid.UUID | None = None,
) -> ResponseT:
    model = base.column_descriptions[0]["entity"]
    if default_sort is None:
        default_sort = model.created_at
    if tiebreaker is None:
        tiebreaker = model.id
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=schema,
        default_sort=default_sort,
        tiebreaker=tiebreaker,
        params=params,
        current_user=current_user,
    )
    return response_model(
        data=[schema.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


def media_owner_list_response[ResponseT: BaseModel](  # noqa: PLR0913
    *,
    session: Session,
    base: SelectOfScalar[Any],
    response_model: type[ResponseT],
    schema: type[SQLModel],
    read_options: MediaReadOptions,
    current_user: User,
    default_sort: datetime | None = None,
    tiebreaker: uuid.UUID | None = None,
) -> ResponseT:
    if not read_options.owner:
        base = base.where(Plugin.user_id == current_user.id)
    else:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=403,
                detail="The user doesn't have enough privileges",
            )
        base = filter_media_by_owner(
            base,
            owner=read_options.owner,
            current_user=current_user,
            session=session,
        )
    return media_list_response(
        session=session,
        base=base,
        response_model=response_model,
        schema=schema,
        params=read_options,
        current_user=current_user,
        default_sort=default_sort,
        tiebreaker=tiebreaker,
    )
