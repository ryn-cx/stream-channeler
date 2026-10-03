# TODO: Validate
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, Index, PrimaryKeyConstraint

from app.models import TimestampIdAndHashMixin


# TODO: Validate
class UserActionKind(StrEnum):
    tmdb_search = "tmdb_search"
    tmdb_media_info = "tmdb_media_info"
    tmdb_watch_providers = "tmdb_watch_providers"
    match_url = "match_url"
    title_matches = "title_matches"
    import_urls = "import_urls"
    bulk_import_urls = "bulk_import_urls"
    retry_import = "retry_import"
    build_channel_from_title = "build_channel_from_title"
    add_channel_title = "add_channel_title"
    create_channel = "create_channel"
    create_channel_order = "create_channel_order"
    create_comment = "create_comment"
    edit_comment = "edit_comment"
    delete_comment = "delete_comment"
    issue_report = "issue_report"
    import_watch_history = "import_watch_history"
    signup = "signup"
    login_failed = "login_failed"


# TODO: Validate
class UserAction(TimestampIdAndHashMixin, table=True):
    __table_args__ = (
        PrimaryKeyConstraint("id"),
        Index("UserAction-user_id-created_at-index", "user_id", "created_at"),
        Index("UserAction-ip_address-created_at-index", "ip_address", "created_at"),
        Index("UserAction-action-created_at-index", "action", "created_at"),
    )

    user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        ondelete="SET NULL",
    )
    ip_address: str | None = Field(default=None)
    action: str
    details: dict[str, Any] = Field(
        default_factory=dict,
        sa_type=JSONB,
        nullable=False,
    )
