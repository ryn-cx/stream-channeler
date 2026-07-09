import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import Boolean, DateTime, UnaryExpression, asc, desc
from sqlalchemy.orm import InstrumentedAttribute
from sqlmodel import Session, SQLModel, col, func, select
from sqlmodel.sql.expression import SelectOfScalar

from app.constants import MAX_PAGE_SIZE
from app.schemas import FilterOption, ReadOptions, SortOption


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


def _date_str_to_datetime(date_string: str) -> datetime:
    try:
        return datetime.fromisoformat(date_string)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime value: {date_string!r}",
        ) from error


def _apply_datetime_filter[T](
    statement: SelectOfScalar[T],
    column: InstrumentedAttribute[Any],
    value: str | list[str],
) -> SelectOfScalar[T]:
    if not isinstance(value, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Datetime filters expect a [min, max] range.",
        )
    minimum = value[0] if value else ""
    maximum = value[1] if len(value) > 1 else ""
    if minimum:
        statement = statement.where(column >= _date_str_to_datetime(minimum))
    if maximum:
        statement = statement.where(column <= _date_str_to_datetime(maximum))
    return statement


def _apply_filter_options[T](
    statement: SelectOfScalar[T],
    filter_options: list[FilterOption],
    columns: dict[str, InstrumentedAttribute[Any]],
) -> SelectOfScalar[T]:
    for option in filter_options:
        column = _get_column(columns, option.column)
        if isinstance(column.type, DateTime):
            statement = _apply_datetime_filter(statement, column, option.value)
        elif isinstance(column.type, Boolean):
            statement = statement.where(column == (option.value == "true"))
        else:
            statement = statement.where(column.ilike(f"%{option.value}%"))
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

    # Tiebreaker is used to make the order deterministic which is required for
    # pagination to work correctly.
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
) -> tuple[Sequence[T], int, int, bool]:
    model = base.column_descriptions[0]["entity"]
    columns = {field: getattr(model, field) for field in schema.model_fields}
    total_count = session.exec(select(func.count()).select_from(base.subquery())).one()

    if total_count < MAX_PAGE_SIZE:
        # A default sort option needs to be applied for pagination to work correctly.
        ordered = _apply_sort_options(base, [], columns, default_sort, tiebreaker)
        return session.exec(ordered).all(), total_count, total_count, False

    filtered = _apply_filter_options(base, params.filter_options, columns)
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
