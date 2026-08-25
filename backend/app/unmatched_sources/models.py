# TODO: Validate
import uuid
from datetime import datetime

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    SQLModel,
    UniqueConstraint,
)

from app.models import DateTimeField, TimestampIdAndHashMixin
from app.shows.models import Show


# TODO: Validate
class BaseUnmatchedSource(SQLModel):
    provider_name: str = Field(min_length=1)
    plugin_key: str | None = Field(default=None)
    ignored_at: datetime | None = DateTimeField(default=None)


# TODO: Validate
class UnmatchedSource(BaseUnmatchedSource, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint(
            "show_id",
            "provider_name",
            name="UnmatchedSource-show_id-provider_name-unique",
        ),
        Index("UnmatchedSource-show_id-index", "show_id"),
    )

    show_id: uuid.UUID = Field(foreign_key="show.id", ondelete="CASCADE")
    show: Show = Relationship()
