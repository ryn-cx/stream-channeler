# TODO: Validate
import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel


# TODO: Validate
class UserActionOutput(BaseModel):
    id: uuid.UUID
    created_at: datetime
    action: str
    ip_address: str | None
    user_id: uuid.UUID | None
    username: str | None
    email: str | None
    details: dict[str, Any]


# TODO: Validate
class UserActionsPublic(BaseModel):
    data: list[UserActionOutput]
    total_count: int
    filtered_count: int
    is_server_side: bool
