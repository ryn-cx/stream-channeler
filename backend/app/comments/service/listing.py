# TODO: Validate
"""Comment service functions."""

import uuid
from collections import Counter
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlmodel import Session, col, func, select

from app.channels.models import Channel
from app.comments.models import Comment, CommentNotification
from app.comments.schemas import (
    ChannelCommentOutput,
    ChannelCommentsListOutput,
    CommentOutput,
    CommentScope,
    CommentsListOutput,
)
from app.comments.service.notifications import unread_notification_count
from app.users.models import User

COMMENTS_PAGE_SIZE = 20


# TODO: Validate
def _reply_counts(
    session: Session,
    comment_ids: Sequence[uuid.UUID],
) -> dict[uuid.UUID, int]:
    """Return how many direct replies each of `comment_ids` has."""
    if not comment_ids:
        return {}
    rows = session.exec(
        select(Comment.parent_comment_id, func.count())
        .where(col(Comment.parent_comment_id).in_(comment_ids))
        .group_by(col(Comment.parent_comment_id)),
    ).all()
    return {parent_id: count for parent_id, count in rows if parent_id is not None}


# TODO: Validate
def _output(comment: Comment, reply_count: int = 0) -> CommentOutput:
    return CommentOutput(
        id=comment.id,
        channel_id=comment.channel_id,
        parent_comment_id=comment.parent_comment_id,
        user_id=comment.user_id,
        author=comment.user.username,
        body=comment.body,
        created_at=comment.created_at,
        modified_at=comment.modified_at,
        reply_count=reply_count,
    )


# TODO: Validate
def _outputs_with_reply_counts(
    session: Session,
    comments: Sequence[Comment],
) -> list[CommentOutput]:
    counts = _reply_counts(session, [comment.id for comment in comments])
    return [_output(comment, counts.get(comment.id, 0)) for comment in comments]


# TODO: Validate
def _comment_page(
    session: Session,
    *,
    channel_id: uuid.UUID,
    parent_comment_id: uuid.UUID | None,
    offset: int,
    limit: int,
) -> CommentsListOutput:
    """Return one page of the comments that share a parent, oldest first."""
    parent_condition = (
        col(Comment.parent_comment_id).is_(None)
        if parent_comment_id is None
        else col(Comment.parent_comment_id) == parent_comment_id
    )
    total_count = session.exec(
        select(func.count())
        .select_from(Comment)
        .where(Comment.channel_id == channel_id, parent_condition),
    ).one()
    comments = session.exec(
        select(Comment)
        .where(Comment.channel_id == channel_id, parent_condition)
        .order_by(col(Comment.created_at).asc())
        .offset(offset)
        .limit(limit),
    ).all()
    return CommentsListOutput(
        comments=_outputs_with_reply_counts(session, comments),
        total_count=total_count,
    )


# TODO: Validate
def get_comments(
    session: Session,
    channel: Channel,
    offset: int = 0,
    limit: int = COMMENTS_PAGE_SIZE,
) -> CommentsListOutput:
    """Return one page of the top level `Comment`s on a `Channel`."""
    return _comment_page(
        session,
        channel_id=channel.id,
        parent_comment_id=None,
        offset=offset,
        limit=limit,
    )


# TODO: Validate
def _descendants(session: Session, comment: Comment) -> list[Comment]:
    """Return every comment below `comment`, at any depth, oldest first."""
    descendant_ids = (
        select(col(Comment.id))
        .where(col(Comment.parent_comment_id) == comment.id)
        .cte("descendant_ids", recursive=True)
    )
    descendant_ids = descendant_ids.union_all(
        select(col(Comment.id)).join(
            descendant_ids,
            col(Comment.parent_comment_id) == descendant_ids.c.id,
        ),
    )
    return list(
        session.exec(
            select(Comment)
            .where(col(Comment.id).in_(select(descendant_ids.c.id)))
            .order_by(col(Comment.created_at).asc()),
        ).all(),
    )


# TODO: Validate
def get_replies(session: Session, comment: Comment) -> CommentsListOutput:
    """Return the whole thread below a `Comment`, nested by parent.

    The entire subtree is loaded in one query so expanding a comment reveals every
    reply underneath it rather than one level at a time.
    """
    descendants = _descendants(session, comment)
    counts = Counter(descendant.parent_comment_id for descendant in descendants)
    outputs = {
        descendant.id: _output(descendant, counts[descendant.id])
        for descendant in descendants
    }

    roots: list[CommentOutput] = []
    for descendant in descendants:
        output = outputs[descendant.id]
        if descendant.parent_comment_id == comment.id:
            roots.append(output)
        elif parent := outputs.get(descendant.parent_comment_id):
            parent.replies.append(output)

    return CommentsListOutput(comments=roots, total_count=len(descendants))


# TODO: Validate
def get_channel_comments(  # noqa: PLR0913 - Paging plus scope plus filter.
    session: Session,
    user: User,
    offset: int = 0,
    limit: int = COMMENTS_PAGE_SIZE,
    scope: CommentScope = CommentScope.owned,
    *,
    unread_only: bool = False,
) -> ChannelCommentsListOutput:
    """Return one page of `Comment`s on channels, newest first.

    The `owned` scope is limited to the `User`'s own channels; `all` covers every
    channel and is only reachable by a superuser.
    """
    if scope == CommentScope.all and not user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only a superuser can read every channel's comments.",
        )
    statement = (
        select(Comment, Channel.name, CommentNotification)
        .join(Channel, col(Channel.id) == col(Comment.channel_id))
        .outerjoin(
            CommentNotification,
            (col(CommentNotification.comment_id) == col(Comment.id))
            & (col(CommentNotification.user_id) == user.id),
        )
    )
    if scope == CommentScope.owned:
        statement = statement.where(Channel.user_id == user.id)
    if unread_only:
        statement = statement.where(col(CommentNotification.read_at).is_(None))

    total_count = session.exec(
        select(func.count()).select_from(statement.subquery()),
    ).one()

    rows = session.exec(
        statement.order_by(col(Comment.created_at).desc()).offset(offset).limit(limit),
    ).all()
    counts = _reply_counts(session, [comment.id for comment, _, _ in rows])

    comments = [
        ChannelCommentOutput(
            **_output(comment, counts.get(comment.id, 0)).model_dump(),
            channel_name=channel_name,
            is_read=notification is None or notification.read_at is not None,
        )
        for comment, channel_name, notification in rows
    ]

    return ChannelCommentsListOutput(
        comments=comments,
        total_count=total_count,
        unread_count=unread_notification_count(session, user),
    )
