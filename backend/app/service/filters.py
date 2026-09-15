# TODO: Validate
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    Uuid,
    cast,
)
from sqlalchemy.orm import InstrumentedAttribute
from sqlmodel.sql.expression import SelectOfScalar

from app.schemas import (
    FilterOption,
)


# TODO: Validate
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


# TODO: Validate
def _date_str_to_datetime(date_string: str) -> datetime:
    try:
        return datetime.fromisoformat(date_string)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime value: {date_string!r}",
        ) from error


# TODO: Validate
def _str_to_number(number_string: str) -> float:
    try:
        return float(number_string)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid number value: {number_string!r}",
        ) from error


# TODO: Validate
def _str_to_uuid(uuid_string: str) -> uuid.UUID:
    try:
        return uuid.UUID(uuid_string)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid uuid value: {uuid_string!r}",
        ) from error


# TODO: Validate
def _range_bounds(value: str | list[str], label: str) -> tuple[str, str]:
    if not isinstance(value, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} filters expect a [minimum, maximum] range.",
        )
    minimum = value[0] if value else ""
    maximum = value[1] if len(value) > 1 else ""
    return minimum, maximum


# TODO: Validate
def _apply_datetime_filter[T](
    statement: SelectOfScalar[T],
    column: InstrumentedAttribute[Any],
    value: str | list[str],
) -> SelectOfScalar[T]:
    minimum, maximum = _range_bounds(value, "Datetime")
    if minimum:
        statement = statement.where(column >= _date_str_to_datetime(minimum))
    if maximum:
        statement = statement.where(column <= _date_str_to_datetime(maximum))
    return statement


# TODO: Validate
def _apply_number_filter[T](
    statement: SelectOfScalar[T],
    column: InstrumentedAttribute[Any],
    value: str | list[str],
) -> SelectOfScalar[T]:
    minimum, maximum = _range_bounds(value, "Number")
    if minimum:
        statement = statement.where(column >= _str_to_number(minimum))
    if maximum:
        statement = statement.where(column <= _str_to_number(maximum))
    return statement


# TODO: Validate
def _apply_filter_options[T](
    statement: SelectOfScalar[T],
    filter_options: list[FilterOption],
    columns: dict[str, InstrumentedAttribute[Any]],
) -> SelectOfScalar[T]:
    for option in filter_options:
        column = _get_column(columns, option.column)
        if isinstance(column.type, DateTime):
            statement = _apply_datetime_filter(statement, column, option.value)
        elif isinstance(column.type, (Integer, Float, Numeric)):
            statement = _apply_number_filter(statement, column, option.value)
        elif isinstance(column.type, Boolean):
            statement = statement.where(column == (option.value == "true"))
        elif isinstance(column.type, Uuid):
            if isinstance(option.value, str) and (text := option.value.strip()):
                statement = statement.where(column == _str_to_uuid(text))
        elif isinstance(option.value, str) and (text := option.value.strip()):
            statement = statement.where(cast(column, String).ilike(f"%{text}%"))

    return statement
