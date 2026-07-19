# TODO: Validate
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    UnaryExpression,
    asc,
    cast,
    desc,
)
from sqlalchemy.orm import InstrumentedAttribute
from sqlmodel import Session, SQLModel, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.constants import DEFAULT_SERVER_SIDE_THRESHOLD
from app.models import Visibility
from app.plugins.models import Plugin
from app.schemas import (
    FilterOption,
    ReadOptions,
    RecordScope,
    ScopedReadOptions,
    SortOption,
)
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


def _date_str_to_datetime(date_string: str) -> datetime:
    try:
        return datetime.fromisoformat(date_string)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid datetime value: {date_string!r}",
        ) from error


def _str_to_number(number_string: str) -> float:
    try:
        return float(number_string)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid number value: {number_string!r}",
        ) from error


def _range_bounds(value: str | list[str], label: str) -> tuple[str, str]:
    if not isinstance(value, list):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{label} filters expect a [minimum, maximum] range.",
        )
    minimum = value[0] if value else ""
    maximum = value[1] if len(value) > 1 else ""
    return minimum, maximum


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
        elif isinstance(option.value, str) and (text := option.value.strip()):
            statement = statement.where(cast(column, String).ilike(f"%{text}%"))

    return statement


def _apply_sort_options[T](  # noqa: PLR0913
    statement: SelectOfScalar[T],
    sort_options: list[SortOption],
    columns: dict[str, InstrumentedAttribute[Any]],
    default_sort: datetime | None,
    tiebreaker: uuid.UUID | None,
    *,
    random_tiebreaker: bool = False,
) -> SelectOfScalar[T]:
    order_by: list[UnaryExpression[Any]] = [
        desc(column) if option.desc else asc(column)
        for option in sort_options
        if (column := _get_column(columns, option.column))
    ]
    if not order_by:
        order_by.append(desc(col(default_sort)))

    # Break ties randomly (e.g. to shuffle equally scored rows) rather than by the
    # stable `id`. Only sound when the whole list is read in one query, since a fresh
    # `random()` per query would make offset/limit pages overlap.
    if random_tiebreaker:
        order_by.append(func.random())
    else:
        order_by.append(asc(col(tiebreaker)))

    return statement.order_by(*order_by)


def get_read_results[T](  # noqa: PLR0913
    session: Session,
    base: SelectOfScalar[T],
    *,
    schema: type[SQLModel],
    default_sort: datetime | None,
    tiebreaker: uuid.UUID | None,
    params: ReadOptions,
    current_user: User | None,
    extra_columns: dict[str, Any] | None = None,
    random_tiebreaker: bool = False,
) -> tuple[Sequence[T], int, int, bool]:
    if current_user:
        threshold = current_user.server_side_threshold
    else:
        threshold = DEFAULT_SERVER_SIDE_THRESHOLD

    model = base.column_descriptions[0]["entity"]
    columns = {
        field: getattr(model, field)
        for field in schema.model_fields
        if hasattr(model, field)
    }
    if extra_columns:
        columns.update(extra_columns)
    total_count = session.exec(select(func.count()).select_from(base.subquery())).one()

    if total_count < threshold:
        ordered = _apply_sort_options(
            base,
            [],
            columns,
            default_sort,
            tiebreaker,
            random_tiebreaker=random_tiebreaker,
        )
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


def _owning_plugin(record: Any) -> Plugin:  # noqa: ANN401 - Any media record.
    """Return the `Plugin` that owns `record`.

    Walks `parent` rather than calling `_root_record`, which issues a query per
    record; every media list eager-loads this chain, so walking it costs nothing.
    """
    current = record
    while not isinstance(current, Plugin):
        current = current.parent
    return current


def media_row_output[SchemaT: SQLModel](
    record: Any,  # noqa: ANN401 - Any media record.
    viewer: User | None,
    schema: type[SchemaT],
) -> SchemaT:
    """Build a media list row, hiding the owner when its `Plugin` is anonymous.

    A media record's owner is its `Plugin`'s `User`, so the `Plugin`'s `anonymous`
    flag decides this just as a `Channel`'s own flag does. The owner and admins see
    through the anonymity.
    """
    row = schema.model_validate(record)
    plugin = _owning_plugin(record)
    privileged = bool(
        viewer and (viewer.is_superuser or viewer.id == plugin.user_id),
    )
    if plugin.anonymous and not privileged and hasattr(row, "username"):
        row.username = None
    return row


def list_response[ResponseT: BaseModel](  # noqa: PLR0913
    *,
    session: Session,
    base: SelectOfScalar[Any],
    response_model: type[ResponseT],
    schema: type[SQLModel],
    params: ReadOptions,
    current_user: User | None,
    default_sort: datetime | None = None,
    tiebreaker: uuid.UUID | None = None,
    extra_columns: dict[str, Any] | None = None,
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
        extra_columns=extra_columns,
    )
    return response_model(
        data=[media_row_output(row, current_user, schema) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


def scoped_row_output[SchemaT: SQLModel](
    record: Any,  # noqa: ANN401 - Any user-owned model carrying the scoping fields.
    username: str | None,
    viewer: User | None,
    schema: type[SchemaT],
) -> SchemaT:
    privileged = bool(
        viewer and (viewer.is_superuser or viewer.id == record.user_id),
    )
    redacted = record.anonymous and not privileged
    return schema.model_validate(
        record,
        update={
            "user_id": None if redacted else record.user_id,
            "username": None if redacted else username,
        },
    )


def scoped_list_response[ResponseT: BaseModel](  # noqa: PLR0913
    *,
    session: Session,
    model: Any,  # noqa: ANN401 - Any user-owned model carrying the scoping fields.
    viewer: User | None,
    read_options: ScopedReadOptions,
    schema: type[SQLModel],
    response_model: type[ResponseT],
    favorite_model: Any = None,  # noqa: ANN401 - The model's user/record favorite link.
    favorite_record_id: Any = None,  # noqa: ANN401 - The link column referencing model.id.
    random_tiebreaker: bool = False,
) -> ResponseT:
    base = select(model).join(User)
    # `public` is ranked by `score`; the other scopes are newest first.
    default_sort: Any = model.created_at
    if read_options.scope == RecordScope.public:
        base = base.where(model.visibility == Visibility.public)
        default_sort = model.score
    elif read_options.scope == RecordScope.owned:
        if viewer is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        base = base.where(model.user_id == viewer.id)
    elif read_options.scope == RecordScope.favorites:
        if viewer is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        base = base.join(favorite_model, favorite_record_id == model.id).where(
            favorite_model.user_id == viewer.id,
        )
        # A record can stop being readable after it was favorited, so the visibility
        # rules are reapplied rather than trusting the favorite alone.
        if not viewer.is_superuser:
            base = base.where(
                or_(
                    col(model.visibility).in_(
                        (Visibility.public, Visibility.unlisted),
                    ),
                    model.user_id == viewer.id,
                ),
            )
    elif viewer is None or not viewer.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=schema,
        default_sort=default_sort,
        tiebreaker=model.id,
        params=read_options,
        current_user=viewer,
        extra_columns={"username": User.username},
        random_tiebreaker=random_tiebreaker,
    )
    return response_model(
        data=[
            scoped_row_output(record, record.user.username, viewer, schema)
            for record in rows
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )
