# TODO: Validate
from typing import Any

from sqlalchemy import ColumnElement
from sqlmodel import col


# TODO: Validate
def is_plugin_user(
    email: Any,  # noqa: ANN401
) -> ColumnElement[bool]:
    return ~col(email).like("%@%")
