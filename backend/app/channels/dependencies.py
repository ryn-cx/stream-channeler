# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path, status

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels.models import Channel, ChannelShow
from app.media.service import get_owned_record, get_readable_record
from app.shows.dependencies import ReadableShow
from app.users.dependencies import OptionalUser


def require_readable_channel(
    session: SessionDep,
    optional_user: OptionalUser,
    channel_id: uuid.UUID,
) -> Channel:
    """Return a channel if it exists and is readable by the current user."""
    return get_readable_record(session, Channel, channel_id, optional_user)


def require_owned_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_id: Annotated[uuid.UUID, Path()],
) -> Channel:
    """Return a channel if it exists and belongs to the current user."""
    return get_owned_record(session, Channel, channel_id, current_user.id)


def require_readable_channel_readable_show(
    session: SessionDep,
    channel: ReadableChannel,
    show: ReadableShow,
) -> ChannelShow:
    """Return a channel show if it exists and is readable by the current user."""
    if not (channel_show := ChannelShow.get(session, channel, show.id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Show was not found on channel",
        )
    return channel_show


def require_owned_channel_readable_show(
    session: SessionDep,
    channel: OwnedChannel,
    show: ReadableShow,
) -> ChannelShow:
    """Return a channel show if it exists and is editable by the current user.

    The current user must own the channel, and the show must be readable."""
    if not (channel_show := ChannelShow.get(session, channel, show.id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Show was not found on channel",
        )
    return channel_show


OwnedChannel = Annotated[Channel, Depends(require_owned_channel)]
ReadableChannel = Annotated[Channel, Depends(require_readable_channel)]
OwnedChannelReadableShow = Annotated[
    ChannelShow,
    Depends(require_owned_channel_readable_show),
]
ReadableChannelReadableShow = Annotated[
    ChannelShow,
    Depends(require_readable_channel_readable_show),
]
