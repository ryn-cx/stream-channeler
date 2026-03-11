# TODO: Validate
import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Path, Query, status
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels.models import Channel, ChannelShow
from app.media.service import get_user_resource
from app.users.dependencies import OptionalUser


def require_user_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_id: Annotated[uuid.UUID, Path()],
) -> Channel:
    return get_user_resource(session, Channel, channel_id, current_user.id)


UserChannel = Annotated[Channel, Depends(require_user_channel)]


def require_channel(session: SessionDep, channel_id: uuid.UUID) -> Channel:
    """Get a channel if it exists.

    Raises:
        HTTPException: If the channel does not exist.
    """
    if channel := get_channel(session, channel_id):
        return channel

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Channel not found",
    )


def get_channel(session: SessionDep, channel_id: uuid.UUID) -> Channel | None:
    """Get a channel if it exists, without raising an exception.

    Returns:
        Channel if found, None otherwise.
    """
    return session.exec(select(Channel).where(Channel.id == channel_id)).first()


def require_readable_channel(
    session: SessionDep,
    optional_user: OptionalUser,
    channel_id: uuid.UUID,
) -> Channel:
    """Retrieve a channel by ID if it can be read by the current user.

    A channel is readable if any of the following conditions are met:
    - The channel is public.
    - The channel belongs to the current user.
    - The current user is a superuser.

    Raises:
        HTTPException: If the user does not have permission to read the channel.
    """
    channel = require_channel(session, channel_id)

    if _can_read_channel(channel, optional_user):
        return channel

    if not optional_user:
        # 401 because the user can log in which may give them access.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Not authorized to access this Channel",
    )


ReadableChannel = Annotated[Channel, Depends(require_readable_channel)]


def get_readable_channels(
    session: SessionDep,
    optional_user: OptionalUser,
    channel_ids: Annotated[list[uuid.UUID], Query()],
) -> list[Channel]:
    """Retrieve channels by ID if they can be read by the current user.

    A channel is readable if any of the following conditions are met:
    - The channel is public.
    - The channel belongs to the current user.
    - The current user is a superuser.

    Returns:
        List of channels the user has permission to read.
    """
    channels = session.exec(
        select(Channel).where(Channel.id.in_(channel_ids)),  # type: ignore[union-attr]
    ).all()

    return [ch for ch in channels if _can_read_channel(ch, optional_user)]


ReadableChannels = Annotated[list[Channel], Depends(get_readable_channels)]


def require_user_channel_show(
    session: SessionDep,
    channel: UserChannel,
    show_id: uuid.UUID,
) -> ChannelShow:
    """Retrieve a channel show if it belongs to the current user.

    Raises:
        HTTPException: 404 if the show is not found on the channel.
            Ownership is checked by the UserChannel dependency.
    """
    if not (channel_show := ChannelShow.get(session, channel, show_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Show was not found on channel",
        )

    return channel_show


UserChannelShow = Annotated[ChannelShow, Depends(require_user_channel_show)]


def _can_read_channel(channel: Channel, user: OptionalUser) -> bool:
    """Check if a user has read access to a channel."""
    if channel.public:
        return True
    if not user:
        return False
    return user.is_superuser or channel.user_id == user.id
