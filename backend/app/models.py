# TODO: Validate
import uuid
from datetime import datetime

from sqlmodel import DateTime, Field, SQLModel

from app.utils import tz_datetime


# Generic message
class Message(SQLModel):
    message: str


class TimestampIdMixin(SQLModel):
    """Mixin to add created_at, modified_at, and id fields to a model."""

    # This is basically the same as the almost official example of how to implement a
    # created_at timestamp as seen here:
    # https://github.com/fastapi/full-stack-fastapi-template/blob/master/backend/app/models.py
    # call-overload - From the original template
    created_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        default_factory=tz_datetime.now,
    )

    # This is basically the same as the implementation of created_at seen above, but it
    # includes the addition of an onupdate to automatically update the timestamp when
    # the record is modified.
    modified_at: datetime = Field(
        sa_type=DateTime(timezone=True),  # type: ignore[call-overload]
        sa_column_kwargs={"onupdate": tz_datetime.now},
        default_factory=tz_datetime.now,
    )

    id: uuid.UUID = Field(
        unique=True,
        default_factory=uuid.uuid4,
    )
