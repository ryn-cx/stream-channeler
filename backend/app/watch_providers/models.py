# TODO: Validate
from sqlmodel import (
    Field,
    PrimaryKeyConstraint,
    SQLModel,
    UniqueConstraint,
)

from app.models import TimestampIdAndHashMixin


# TODO: Validate
class BaseWatchProvider(SQLModel):
    tmdb_provider_id: int
    name: str = Field(min_length=1)
    logo_url: str | None = Field(default=None)


# TODO: Validate
class WatchProvider(BaseWatchProvider, TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        UniqueConstraint(
            "tmdb_provider_id",
            name="WatchProvider-tmdb_provider_id-unique",
        ),
    )
