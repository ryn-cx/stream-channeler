# TODO: Validate
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import (
    String,
    UnaryExpression,
    asc,
    cast,
    desc,
)
from sqlalchemy.orm import InstrumentedAttribute
from sqlmodel import col, func
from sqlmodel.sql.expression import SelectOfScalar

from app.schemas import (
    SortOption,
)
from app.service.filters import _get_column


# TODO: Validate
def _apply_sort_options[T](  # noqa: PLR0913
    statement: SelectOfScalar[T],
    sort_options: list[SortOption],
    columns: dict[str, InstrumentedAttribute[Any]],
    default_sorts: Sequence[Any],
    tiebreaker: uuid.UUID | None,
    *,
    random_tiebreaker: bool = False,
    random_seed: int | None = None,
) -> SelectOfScalar[T]:
    order_by: list[UnaryExpression[Any]] = [
        desc(column) if option.desc else asc(column)
        for option in sort_options
        if (column := _get_column(columns, option.column))
    ]
    if not order_by:
        order_by.extend(desc(default_sort) for default_sort in default_sorts)

    # Break ties randomly (e.g. to shuffle equally scored rows) rather than by the
    # stable `id`. A seed makes the shuffle deterministic, so offset/limit pages of
    # the same seeded read stay consistent; an unseeded `random()` is only sound when
    # the whole list is read in one query.
    if random_tiebreaker and random_seed is not None:
        order_by.append(
            asc(func.md5(func.concat(cast(col(tiebreaker), String), str(random_seed)))),
        )
    elif random_tiebreaker:
        order_by.append(func.random())
    else:
        order_by.append(asc(col(tiebreaker)))

    return statement.order_by(*order_by)
