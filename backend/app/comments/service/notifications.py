# TODO: Validate
"""Comment service functions."""

import uuid

from sqlmodel import Session, col, func, select

from app.comments.models import CommentNotification
from app.schemas import Message
from app.users.models import User
from app.utils import tz_datetime


# TODO: Validate
def unread_notification_count(session: Session, user: User) -> int:
    """Return how many comment notifications the `User` has not read yet."""
    statement = (
        select(func.count())
        .select_from(CommentNotification)
        .where(
            CommentNotification.user_id == user.id,
            col(CommentNotification.read_at).is_(None),
        )
    )
    return session.exec(statement).one()


# TODO: Validate
def mark_notifications_read(
    session: Session,
    user: User,
    comment_id: uuid.UUID | None = None,
) -> Message:
    """Mark one comment notification as read, or every unread one when omitted."""
    statement = select(CommentNotification).where(
        CommentNotification.user_id == user.id,
        col(CommentNotification.read_at).is_(None),
    )
    if comment_id is not None:
        statement = statement.where(CommentNotification.comment_id == comment_id)

    for notification in session.exec(statement).all():
        notification.read_at = tz_datetime.now()
        session.add(notification)
    session.commit()
    return Message(message="Notifications marked as read")
