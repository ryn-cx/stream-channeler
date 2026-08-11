# TODO: Validate
"""Comment schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum

from sqlmodel import Field, SQLModel

from app.comments.models import BaseComment, Comment
from app.schemas import BaseInput, BaseUpdateWithoutKey


# TODO: Validate
class CommentScope(StrEnum):
    """Which comments a listing returns."""

    owned = "owned"
    all = "all"


# TODO: Validate
class CommentCreate(BaseInput, BaseComment):
    """Schema for creating a `Comment`."""

    parent_comment_id: uuid.UUID | None = None


# TODO: Validate
class CommentUpdate(BaseUpdateWithoutKey[Comment]):
    """Schema for updating a `Comment`."""

    body: str | None = None


# TODO: Validate
class CommentOutput(BaseComment):
    """Schema for returning a `Comment`.

    A channel's comment list only returns top level comments, leaving `replies`
    empty and using `reply_count` to say whether there is a thread to expand. The
    thread endpoint fills `replies` with the whole tree below a comment.
    """

    id: uuid.UUID
    channel_id: uuid.UUID
    parent_comment_id: uuid.UUID | None
    user_id: uuid.UUID
    author: str
    created_at: datetime
    modified_at: datetime
    reply_count: int = Field(default=0)
    replies: list[CommentOutput] = Field(default_factory=list)


# TODO: Validate
class ChannelCommentOutput(CommentOutput):
    """Schema for a `Comment` shown outside of its own channel's page."""

    channel_name: str | None
    is_read: bool


# TODO: Validate
class CommentsListOutput(SQLModel):
    """Schema for returning one page of `Comment`s."""

    comments: list[CommentOutput] = Field(default_factory=list)
    total_count: int = Field(default=0)


# TODO: Validate
class ChannelCommentsListOutput(SQLModel):
    """Schema for returning every `Comment` left on a `User`'s `Channel`s."""

    comments: list[ChannelCommentOutput] = Field(default_factory=list)
    total_count: int = Field(default=0)
    unread_count: int = Field(default=0)
