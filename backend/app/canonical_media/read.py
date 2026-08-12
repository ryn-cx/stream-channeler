# TODO: Validate
"""Serve a page of canonical rows.

The media list helpers decide who may see a record by walking it up to the
`Plugin` that holds it, and hide the owner's name where that `Plugin` is
anonymous. A canonical row has neither: it is the media itself rather than one
website's listing of it, so there is no owner to hide and nothing to scope by.
What is left is the paging, sorting and filtering, used on their own, behind the
admin-only endpoints that are the only way in.
"""

from typing import Any

from pydantic import BaseModel
from sqlmodel import Session, SQLModel
from sqlmodel.sql.expression import SelectOfScalar

from app.schemas import ReadOptions
from app.service import get_read_results
from app.users.models import User


# TODO: Validate
def canonical_list_response[ResponseT: BaseModel](  # noqa: PLR0913
    *,
    session: Session,
    base: SelectOfScalar[Any],
    response_model: type[ResponseT],
    schema: type[SQLModel],
    read_options: ReadOptions,
    current_user: User,
    extra_columns: dict[str, Any] | None = None,
) -> ResponseT:
    """Return a page of canonical rows, sorted and filtered as asked for."""
    model = base.column_descriptions[0]["entity"]
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=schema,
        default_sort=model.created_at,
        tiebreaker=model.id,
        params=read_options,
        current_user=current_user,
        extra_columns=extra_columns,
    )
    return response_model(
        data=[schema.model_validate(row) for row in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )
