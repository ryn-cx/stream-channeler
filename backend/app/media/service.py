# TODO: Validate

import json
import uuid
from collections.abc import Callable, Sequence
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from fastapi import HTTPException, Path
from sqlalchemy import DateTime, String, and_, asc, cast, desc, or_
from sqlmodel import Session, SQLModel, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.auth.dependencies import CurrentUser, SessionDep
from app.schemas import MEDIA_MODELS, Message
from app.users.dependencies import OptionalUser
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
            record_user_id = result.get_user_id(session)
            plugin_user_id = get_or_create_plugin_user(session=session).id
            if optional_user.id == record_user_id:
                return result
            if optional_user.is_superuser and record_user_id == plugin_user_id:
                return result
            raise HTTPException(
                status_code=403,
                detail=f"Not authorized to access this {model.__name__}",
            )
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")

    return dependency


def owned_record[T: MEDIA_MODELS](
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
            record_user_id = record.get_user_id(session)
            if current_user.id == record_user_id:
                return record
            plugin_user_id = get_or_create_plugin_user(session=session).id
            if current_user.is_superuser and record_user_id == plugin_user_id:
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


SERVER_SIDE_THRESHOLD = 10_000


class MediaOwner(StrEnum):
    """Which owner's records a table query targets.

    Own content is represented by an unset `owner` (`None`), so this enum only
    covers the admin-only views.
    """

    official = "official"
    others = "others"


def apply_filters[T](
    statement: SelectOfScalar[T],
    filters_json: str | None,
    columns: dict[str, Any],
    date_range_columns: set[str],
) -> SelectOfScalar[T]:
    """Apply the frontend's `ColumnFiltersState` (JSON) to the query."""
    if not filters_json:
        return statement
    for entry in json.loads(filters_json):
        column = columns.get(entry["id"])
        if column is None:
            continue
        if entry["id"] in date_range_columns:
            statement = _apply_date_range(statement, column, entry["value"])
        else:
            text = str(entry["value"]).strip()
            if text:
                statement = statement.where(cast(column, String).ilike(f"%{text}%"))
    return statement


def _apply_date_range[T](
    statement: SelectOfScalar[T],
    column: Any,  # noqa: ANN401 - SQLAlchemy column attribute
    value: dict[str, Any],
) -> SelectOfScalar[T]:
    minimum = value.get("minimumDate")
    maximum = value.get("maximumDate")
    hide_blanks = value.get("hideBlanks")
    if not minimum and not maximum and not hide_blanks:
        return statement

    bounds = [col(column).is_not(None)]
    if minimum:
        bounds.append(column >= datetime.fromisoformat(minimum))
    if maximum:
        bounds.append(column <= datetime.fromisoformat(maximum))
    in_range = and_(*bounds)

    if hide_blanks:
        return statement.where(in_range)
    return statement.where(or_(col(column).is_(None), in_range))


def apply_sorting[T](
    statement: SelectOfScalar[T],
    sorting_json: str | None,
    columns: dict[str, Any],
    tiebreaker: Any,  # noqa: ANN401 - SQLAlchemy column attribute
) -> SelectOfScalar[T]:
    order_by = []
    if sorting_json:
        for entry in json.loads(sorting_json):
            column = columns.get(entry["id"])
            if column is not None:
                order_by.append(desc(column) if entry.get("desc") else asc(column))
    # Keep paging deterministic when the sorted column has ties.
    order_by.append(asc(tiebreaker))
    return statement.order_by(*order_by)


def build_table_columns(
    model: type[SQLModel],
    schema: type[SQLModel],
) -> tuple[dict[str, Any], set[str]]:
    columns: dict[str, Any] = {
        field: getattr(model, field) for field in schema.model_fields
    }
    date_range_columns = {
        name for name, column in columns.items() if isinstance(column.type, DateTime)
    }
    return columns, date_range_columns


def build_table_page[T](  # noqa: PLR0913 - keyword-only table parameters
    session: Session,
    base: SelectOfScalar[T],
    *,
    columns: dict[str, Any],
    date_range_columns: set[str],
    tiebreaker: Any,  # noqa: ANN401 - SQLAlchemy column attribute
    offset: int,
    limit: int,
    sorting: str | None,
    filters: str | None,
) -> tuple[Sequence[T], int, bool]:
    total = session.exec(select(func.count()).select_from(base.subquery())).one()
    if total < SERVER_SIDE_THRESHOLD:
        return session.exec(base).all(), total, False

    filtered = apply_filters(base, filters, columns, date_range_columns)
    count = session.exec(select(func.count()).select_from(filtered.subquery())).one()
    page = (
        apply_sorting(filtered, sorting, columns, tiebreaker)
        .offset(offset)
        .limit(limit)
    )
    return session.exec(page).all(), count, True
