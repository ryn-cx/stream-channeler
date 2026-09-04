# TODO: Validate
"""Comment service functions."""

import uuid

from fastapi import HTTPException
from sqlmodel import Session, select

from app.channels.models import Channel
from app.comments.models import Comment, CommentNotification
from app.comments.schemas import (
    CommentCreate,
    CommentOutput,
    CommentUpdate,
)
from app.comments.service.listing import _output, _reply_counts
from app.schemas import Message
from app.users.models import User


# TODO: Validate
def create_comment(
    session: Session,
    user: User,
    channel: Channel,
    comment_input: CommentCreate,
) -> CommentOutput:
    """Create a `Comment` on a `Channel` and notify the people involved."""
    if comment_input.parent_comment_id is not None:
        parent = session.exec(
            select(Comment).where(Comment.id == comment_input.parent_comment_id),
        ).first()
        if parent is None or parent.channel_id != channel.id:
            raise HTTPException(
                status_code=404,
                detail="Parent comment was not found on channel",
            )
    else:
        parent = None

    comment = Comment(
        body=comment_input.body,
        channel_id=channel.id,
        user_id=user.id,
        parent_comment_id=comment_input.parent_comment_id,
    )
    session.add(comment)
    session.flush()

    for notified_user_id in _users_to_notify(channel, parent, user):
        session.add(
            CommentNotification(user_id=notified_user_id, comment_id=comment.id),
        )

    session.commit()
    session.refresh(comment)
    return _output(comment)


# TODO: Validate
def _users_to_notify(
    channel: Channel,
    parent: Comment | None,
    author: User,
) -> set[uuid.UUID]:
    """Return the users notified about a new comment, never including its author."""
    notified = {channel.user_id}
    if parent is not None:
        notified.add(parent.user_id)
    return notified - {author.id}


# TODO: Validate
def update_comment(
    session: Session,
    comment: Comment,
    comment_input: CommentUpdate,
) -> CommentOutput:
    """Update a `Comment`."""
    comment_input.update(session, comment)
    return _output(comment, _reply_counts(session, [comment.id]).get(comment.id, 0))


# TODO: Validate
def delete_comment(session: Session, comment: Comment) -> Message:
    """Delete a `Comment` and every reply nested underneath it."""
    session.delete(comment)
    session.commit()
    return Message(message="Comment deleted successfully")
