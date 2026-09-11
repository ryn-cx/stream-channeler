# TODO: Validate
"""Telling a canonical row apart from a non-canonical one.

Canonical and non-canonical rows share a table, and a single flag column is the
whole of what says which of the two a row is. Neither a `Title` nor an `Episode` names
in a column the records it stands for - a website mixes two titles into one page
and runs two episodes together in one listing, and each row stands for every one
of them equally - so a row says outright which kind it is rather than leaving it
to be read off a pointer. Every query naming one of these tables means one of the
two and never both, so it says which here rather than leaving it to the reader.

The entity is taken rather than the class because most of the callers are joins
that reach the same table more than once and so work through `aliased`, and only
the entity knows which of those the column belongs to.
"""

from typing import Any, cast

from sqlalchemy import inspect
from sqlalchemy.sql.expression import ColumnElement


# TODO: Validate
def _linked_flag(entity: Any) -> Any:  # noqa: ANN401 - The canonical flag of whichever entity was given.
    field = inspect(entity).mapper.class_.LINKED_FLAG_FIELD
    return getattr(entity, field)


# TODO: Validate
def is_not_linked(entity: Any) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the filter matching the canonical rows of `entity`."""
    return cast("ColumnElement[bool]", _linked_flag(entity).is_(False))


# TODO: Validate
def is_linked(entity: Any) -> ColumnElement[bool]:  # noqa: ANN401 - A model class or an alias of one.
    """Return the filter matching the non-canonical rows of `entity`."""
    return cast("ColumnElement[bool]", _linked_flag(entity).is_(True))
