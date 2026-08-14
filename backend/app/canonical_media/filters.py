# TODO: Validate
"""Telling a canonical row apart from a non-canonical one.

Canonical and non-canonical rows share a table, and which of the two a row is is
said by a column of its own. A non-canonical `Episode` stands for one canonical
episode at most, so the pointer naming that episode answers it: a row that points
at nothing is canonical. A non-canonical `Show` stands for however many canonical
shows the website mixed into it and names none of them in a column, so it says
which it is outright in `is_canonical`. Every query naming one of these tables
means one of the two and never both, so it says which here rather than leaving it
to the reader.

The entity is taken rather than the class because most of the callers are joins
that reach the same table more than once and so work through `aliased`, and only
the entity knows which of those the column belongs to.
"""

from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, inspect
from sqlalchemy.sql.expression import ColumnElement


# TODO: Validate
def _canonical_id(entity: Any) -> Any:  # noqa: ANN401 - The canonical pointer of whichever entity was given.
    field = inspect(entity).mapper.class_.CANONICAL_ID_FIELD
    return getattr(entity, field)


# TODO: Validate
def _canonical_flag(entity: Any) -> Any:  # noqa: ANN401 - The canonical flag of whichever entity was given, where it carries one.
    field = getattr(inspect(entity).mapper.class_, "CANONICAL_FLAG_FIELD", None)
    if field is None:
        return None
    return getattr(entity, field)


# TODO: Validate
def is_canonical(entity: Any) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the filter matching the canonical rows of `entity`."""
    flag = _canonical_flag(entity)
    if flag is not None:
        return cast("ColumnElement[bool]", flag.is_(True))
    return cast("ColumnElement[bool]", _canonical_id(entity).is_(None))


# TODO: Validate
def is_non_canonical(entity: Any) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the filter matching the non-canonical rows of `entity`."""
    flag = _canonical_flag(entity)
    if flag is not None:
        return cast("ColumnElement[bool]", flag.is_(False))
    return cast("ColumnElement[bool]", _canonical_id(entity).is_not(None))


# TODO: Validate
def canonical_id_column(entity: Any) -> ColumnElement[UUID]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the canonical row `entity` stands for, or `entity` where it is one.

    A row that points at nothing is canonical, so the row it stands for is
    itself. Reading the pointer alone leaves those rows as `NULL` and drops them
    out of every comparison the pointer is used in.
    """
    return cast(
        "ColumnElement[UUID]",
        func.coalesce(_canonical_id(entity), entity.id),
    )


# TODO: Validate
def canonical_id_of(row: Any) -> UUID:  # noqa: ANN401 - A model instance.
    """Return the canonical row `row` stands for, which is `row` where it is one."""
    return getattr(row, row.CANONICAL_ID_FIELD) or row.id
