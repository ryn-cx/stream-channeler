# TODO: Validate


"""Comment routes."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import SessionDep
from app.channels.dependencies import ReadableChannel
from app.comments.dependencies import ReadableComment
from app.comments.schemas import (
    CommentsListOutput,
)
from app.comments.service import (
    COMMENTS_PAGE_SIZE,
    get_comments,
    get_replies,
)

comments_router = APIRouter(prefix="/comments", tags=["comments"])


channel_comments_router = APIRouter(
    prefix="/channels/{channel_id}/comments",
    tags=["comments"],
)


# TODO: Validate
@channel_comments_router.get("")
def read_channel_comments(
    session: SessionDep,
    channel: ReadableChannel,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = COMMENTS_PAGE_SIZE,
) -> CommentsListOutput:
    """Get one page of the top level `Comment`s on a `Channel`."""
    return get_comments(session, channel, offset, limit)


# TODO: Validate
@comments_router.get("/{comment_id}/replies")  # noqa: FAST003 - Used by ReadableComment.
def read_comment_replies(
    session: SessionDep,
    comment: ReadableComment,
) -> CommentsListOutput:
    """Get the whole thread below a `Comment`, nested by parent."""
    return get_replies(session, comment)


router = APIRouter()
router.include_router(comments_router)
router.include_router(channel_comments_router)
