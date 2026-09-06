# TODO: Validate
from typing import Any

from sqlalchemy import ColumnElement
from sqlmodel import col

PLUGIN_USER_EMAIL_DOMAIN = "StreamChanneler.Com"


# TODO: Validate
def plugin_user_email(plugin_name: str) -> str:
    return f"{plugin_name}@{PLUGIN_USER_EMAIL_DOMAIN}"


# TODO: Validate
def is_plugin_user(
    email: Any,  # noqa: ANN401 - The `User.email` column of whichever alias is asked.
) -> ColumnElement[bool]:
    return col(email).ilike(f"%@{PLUGIN_USER_EMAIL_DOMAIN}")
