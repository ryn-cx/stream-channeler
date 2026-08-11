# TODO: Validate
"""Comment models."""

import uuid
from datetime import datetime
from typing import Optional, override

from sqlmodel import (
    Field,
    Index,
    PrimaryKeyConstraint,
    Relationship,
    Session,
    SQLModel,
)

from app.channels.models import Channel
from app.models import DateTimeField, RootRecordMixin, TimestampIdAndHashMixin
from app.users.models import User


# TODO: Validate
class BaseComment(SQLModel):
    """Base model representing a `Comment` left on a `Channel`."""

    body: str = Field(min_length=1)


# TODO: Validate
class Comment(BaseComment, TimestampIdAndHashMixin, RootRecordMixin, table=True):
    """Model representing a `Comment` left on a `Channel`.

    A comment either belongs directly to the channel or replies to another comment,
    which nests to any depth.
    """

    __table_args__ = (
        PrimaryKeyConstraint("id"),
        # Used to list every comment on a channel.
        Index("Comment-channel_id-index", "channel_id"),
        # Used to list the replies to a comment.
        Index("Comment-parent_comment_id-index", "parent_comment_id"),
        # Used to list every comment written by a user.
        Index("Comment-user_id-index", "user_id"),
    )

    channel_id: uuid.UUID = Field(foreign_key="channel.id", ondelete="CASCADE")
    channel: Channel = Relationship(back_populates="comments")

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")
    user: User = Relationship()

    parent_comment_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="comment.id",
        ondelete="CASCADE",
    )
    # SQLModel needs the quoted forward reference to map a self referencing
    # relationship, so the annotation cannot be unquoted here.
    replies: list["Comment"] = Relationship(  # noqa: UP037
        back_populates="parent_comment",
        cascade_delete=True,
    )
    parent_comment: Optional["Comment"] = Relationship(  # noqa: UP037, UP045
        back_populates="replies",
        sa_relationship_kwargs={"remote_side": "Comment.id"},
    )

    notifications: list["CommentNotification"] = Relationship(  # noqa: UP037
        back_populates="comment",
        cascade_delete=True,
    )

    # TODO: Validate
    @override
    def _root_record(self, session: Session) -> Channel:
        return self.channel

    # TODO: Validate
    @override
    def owner_id(self, _session: Session) -> uuid.UUID:
        """Return the author of the comment rather than the channel's owner.

        Only the author may edit or delete their own comment, so ownership cannot
        come from the channel the comment was left on.
        """
        return self.user_id


# TODO: Validate
class CommentNotification(TimestampIdAndHashMixin, table=True):
    """Model representing a `User` being notified about a `Comment`."""

    __table_args__ = (
        # Each user is notified at most once per comment; the leading column also
        # serves lookups of a user's notifications.
        PrimaryKeyConstraint("user_id", "comment_id"),
        # Used by cascade deletion when a comment is deleted.
        Index("CommentNotification-comment_id-index", "comment_id"),
    )

    user_id: uuid.UUID = Field(foreign_key="user.id", ondelete="CASCADE")

    comment_id: uuid.UUID = Field(foreign_key="comment.id", ondelete="CASCADE")
    comment: Comment = Relationship(back_populates="notifications")

    read_at: datetime | None = DateTimeField(default=None)

    # TODO: Validate
    def owner_id(self, _session: Session) -> uuid.UUID:
        """Return the `id` of the notified `User`."""
        return self.user_id

    # TODO: Validate
    def is_publically_readable(self, _session: Session) -> bool:
        """Return false because a notification is only visible to its `User`."""
        return False
