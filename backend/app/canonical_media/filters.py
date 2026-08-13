# TODO: Validate
"""Telling a canonical row apart from a copy of one.

A canonical row and the copies of it share a table, and which of the two a row is
is said by the pointer a copy carries to the row it is a copy of: a row that
points at nothing is the canonical one. Every query naming one of these tables
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
def is_canonical(entity: Any) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the filter matching the canonical rows of `entity`."""
    return cast("ColumnElement[bool]", _canonical_id(entity).is_(None))


# TODO: Validate
def is_copy(entity: Any) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the filter matching the copy rows of `entity`."""
    return cast("ColumnElement[bool]", _canonical_id(entity).is_not(None))


# TODO: Validate
def canonical_id_column(entity: Any) -> ColumnElement[UUID]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the row `entity` is a copy of, or `entity` itself where it is one.

    A row that points at nothing is the canonical row, so the media it stands for
    is itself. Reading the pointer alone leaves those rows as `NULL` and drops
    them out of every comparison the pointer is used in.
    """
    return cast(
        "ColumnElement[UUID]",
        func.coalesce(_canonical_id(entity), entity.id),
    )


# TODO: Validate
def canonical_id_of(row: Any) -> UUID:  # noqa: ANN401 - A model instance.
    """Return the media `row` stands for, which is `row` itself where it is canonical."""
    return getattr(row, row.CANONICAL_ID_FIELD) or row.id
