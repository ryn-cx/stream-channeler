# TODO: Validate
"""Comment routes."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels.dependencies import ReadableChannel
from app.comments.dependencies import EditableComment, ReadableComment
from app.comments.schemas import (
    ChannelCommentsListOutput,
    CommentCreate,
    CommentOutput,
    CommentScope,
    CommentsListOutput,
    CommentUpdate,
)
from app.comments.service import (
    COMMENTS_PAGE_SIZE,
    create_comment,
    delete_comment,
    get_channel_comments,
    get_comments,
    get_replies,
    mark_notifications_read,
    unread_notification_count,
    update_comment,
)
from app.schemas import Message

channel_comments_router = APIRouter(
    prefix="/channels/{channel_id}/comments",
    tags=["comments"],
)
comments_router = APIRouter(prefix="/comments", tags=["comments"])


@channel_comments_router.get("")
def read_channel_comments(
    session: SessionDep,
    channel: ReadableChannel,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = COMMENTS_PAGE_SIZE,
) -> CommentsListOutput:
    """Get one page of the top level `Comment`s on a `Channel`."""
    return get_comments(session, channel, offset, limit)


@channel_comments_router.post("")
def create_channel_comment(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
    comment_input: CommentCreate,
) -> CommentOutput:
    """Leave a `Comment` on a `Channel` the `User` can read."""
    return create_comment(session, current_user, channel, comment_input)


@comments_router.get("/mine")
def read_my_channel_comments(  # noqa: PLR0913 - Paging plus scope plus filter.
    session: SessionDep,
    current_user: CurrentUser,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = COMMENTS_PAGE_SIZE,
    scope: CommentScope = CommentScope.owned,
    *,
    unread_only: bool = False,
) -> ChannelCommentsListOutput:
    """Get one page of the `Comment`s on the `User`'s `Channel`s, or on all of them."""
    if scope == CommentScope.all and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a superuser can read every channel's comments.",
        )
    return get_channel_comments(
        session,
        current_user,
        offset,
        limit,
        scope,
        unread_only=unread_only,
    )


@comments_router.get("/{comment_id}/replies")  # noqa: FAST003 - Used by ReadableComment.
def read_comment_replies(
    session: SessionDep,
    comment: ReadableComment,
) -> CommentsListOutput:
    """Get the whole thread below a `Comment`, nested by parent."""
    return get_replies(session, comment)


@comments_router.get("/unread-count")
def read_unread_comment_count(session: SessionDep, current_user: CurrentUser) -> int:
    """Get how many comment notifications the `User` has not read."""
    return unread_notification_count(session, current_user)


@comments_router.post("/read")
def mark_comments_read(
    session: SessionDep,
    current_user: CurrentUser,
    comment_id: uuid.UUID | None = None,
) -> Message:
    """Mark one comment notification read, or every unread one when omitted."""
    return mark_notifications_read(session, current_user, comment_id)


@comments_router.patch("/{comment_id}")  # noqa: FAST003 - Used by EditableComment.
def update_channel_comment(
    session: SessionDep,
    comment: EditableComment,
    comment_input: CommentUpdate,
) -> CommentOutput:
    """Update a `Comment` written by the `User`."""
    return update_comment(session, comment, comment_input)


@comments_router.delete("/{comment_id}")  # noqa: FAST003 - Used by EditableComment.
def delete_channel_comment(session: SessionDep, comment: EditableComment) -> Message:
    """Delete a `Comment` written by the `User` and every reply to it."""
    return delete_comment(session, comment)


router = APIRouter()
router.include_router(comments_router)
router.include_router(channel_comments_router)
