import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import (
    Boolean,
    DateTime,
    String,
    UnaryExpression,
    and_,
    asc,
    cast,
    desc,
    or_,
)
from sqlalchemy.orm import InstrumentedAttribute
from sqlmodel import Session, SQLModel, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.constants import SERVER_SIDE_THRESHOLD_DEFAULT
from app.schemas import FilterOption, ReadOptions, SortOption
from app.users.models import User


def _get_column(
    columns: dict[str, InstrumentedAttribute[Any]],
    name: str,
) -> InstrumentedAttribute[Any]:
    if column := columns.get(name):
        return column

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=f"Unknown column: {name!r}",
    )


def _apply_date_range[T](
    statement: SelectOfScalar[T],
    column: InstrumentedAttribute[Any],
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


def _apply_filter_options[T](
    statement: SelectOfScalar[T],
    filter_options: list[FilterOption],
    columns: dict[str, InstrumentedAttribute[Any]],
    date_range_columns: set[str],
) -> SelectOfScalar[T]:
    for option in filter_options:
        column = _get_column(columns, option.column)
        if option.column in date_range_columns and isinstance(option.value, dict):
            statement = _apply_date_range(statement, column, option.value)
        elif isinstance(column.type, Boolean):
            statement = statement.where(column == (option.value == "true"))
        else:
            text = str(option.value).strip()
            if text:
                statement = statement.where(cast(column, String).ilike(f"%{text}%"))
    return statement


def _apply_sort_options[T](
    statement: SelectOfScalar[T],
    sort_options: list[SortOption],
    columns: dict[str, InstrumentedAttribute[Any]],
    default_sort: datetime | None,
    tiebreaker: uuid.UUID,
) -> SelectOfScalar[T]:
    order_by: list[UnaryExpression[Any]] = [
        desc(column) if option.desc else asc(column)
        for option in sort_options
        if (column := _get_column(columns, option.column))
    ]
    if not order_by:
        order_by.append(desc(col(default_sort)))

    order_by.append(asc(col(tiebreaker)))

    return statement.order_by(*order_by)


def get_read_results[T](  # noqa: PLR0913
    session: Session,
    base: SelectOfScalar[T],
    *,
    schema: type[SQLModel],
    default_sort: datetime | None,
    tiebreaker: uuid.UUID,
    params: ReadOptions,
    current_user: User | None,
) -> tuple[Sequence[T], int, int, bool]:
    if current_user:
        threshold = current_user.server_side_threshold
    else:
        threshold = SERVER_SIDE_THRESHOLD_DEFAULT

    model = base.column_descriptions[0]["entity"]
    columns = {field: getattr(model, field) for field in schema.model_fields}
    date_range_columns = {
        name for name, column in columns.items() if isinstance(column.type, DateTime)
    }
    total_count = session.exec(select(func.count()).select_from(base.subquery())).one()

    if total_count < threshold:
        ordered = _apply_sort_options(base, [], columns, default_sort, tiebreaker)
        return session.exec(ordered).all(), total_count, total_count, False

    filtered = _apply_filter_options(
        base,
        params.filter_options,
        columns,
        date_range_columns,
    )
    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            params.sort_options,
            columns,
            default_sort,
            tiebreaker,
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return session.exec(page).all(), total_count, filtered_count, True
