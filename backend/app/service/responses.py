# TODO: Validate
import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status
from pydantic import BaseModel
from sqlmodel import Session, SQLModel, col, func, or_, select
from sqlmodel.sql.expression import SelectOfScalar

from app.constants import DEFAULT_SERVER_SIDE_THRESHOLD
from app.models import Visibility
from app.schemas import (
    ReadOptions,
    RecordScope,
    ScopedReadOptions,
)
from app.service.filters import _apply_filter_options
from app.service.sorting import _apply_sort_options
from app.users.models import User


# TODO: Validate
def get_read_results[T](  # noqa: PLR0913
    session: Session,
    base: SelectOfScalar[T],
    *,
    schema: type[SQLModel],
    default_sorts: Sequence[Any],
    tiebreaker: uuid.UUID | None,
    params: ReadOptions,
    current_user: User | None,
    extra_columns: dict[str, Any] | None = None,
    random_tiebreaker: bool = False,
    random_seed: int | None = None,
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
    filtered = _apply_filter_options(base, params.filter_options, columns)

    if total_count < threshold:
        ordered = _apply_sort_options(
            filtered,
            [],
            columns,
            default_sorts,
            tiebreaker,
            random_tiebreaker=random_tiebreaker,
            random_seed=random_seed,
        )
        rows = session.exec(ordered).all()
        return rows, total_count, len(rows), False

    filtered_count = session.exec(
        select(func.count()).select_from(filtered.subquery()),
    ).one()
    page = (
        _apply_sort_options(
            filtered,
            params.sort_options,
            columns,
            default_sorts,
            tiebreaker,
            random_tiebreaker=random_tiebreaker and random_seed is not None,
            random_seed=random_seed,
        )
        .offset(params.offset)
        .limit(params.limit)
    )
    return session.exec(page).all(), total_count, filtered_count, True


# TODO: Validate
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
        default_sorts=[default_sort],
        tiebreaker=tiebreaker,
        params=params,
        current_user=current_user,
        extra_columns=extra_columns,
    )
    return response_model(
        data=[schema.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


# TODO: Validate
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


# TODO: Validate
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
    rank_by_favorites: bool = False,
) -> ResponseT:
    base = select(model).join(User)
    extra_columns: dict[str, Any] = {"username": User.username}
    favorite_count: Any = None
    if rank_by_favorites:
        counts = (
            select(
                favorite_record_id.label("record_id"),
                func.count().label("favorite_count"),
            )
            .group_by(favorite_record_id)
            .subquery()
        )
        base = base.outerjoin(counts, counts.c.record_id == model.id)
        favorite_count = func.coalesce(counts.c.favorite_count, 0)
        extra_columns["favorite_count"] = favorite_count
    default_sorts: list[Any]
    if favorite_count is None:
        default_sorts = [model.created_at]
    else:
        default_sorts = [favorite_count, model.score, model.created_at]
    if read_options.scope == RecordScope.public:
        base = base.where(model.visibility == Visibility.public)
        if favorite_count is None:
            default_sorts = [model.score, model.created_at]
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
        default_sorts=default_sorts,
        tiebreaker=model.id,
        params=read_options,
        current_user=viewer,
        extra_columns=extra_columns,
        random_tiebreaker=random_tiebreaker,
        random_seed=read_options.random_seed,
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
