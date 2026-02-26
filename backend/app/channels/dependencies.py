import uuid
from typing import Annotated

from fastapi import Depends, HTTPException, Query, status
from sqlmodel import select

from app.auth.dependencies import CurrentUser, SessionDep
from app.channels.models import Channel, ChannelShow
from app.users.dependencies import OptionalUser


def get_channel(session: SessionDep, channel_id: uuid.UUID) -> Channel:
    """Get a channel if it exists.

    Raises:
        HTTPException: If the channel does not exist.
    """
    if channel := safe_get_channel(session, channel_id):
        return channel

    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Channel not found",
    )


def safe_get_channel(session: SessionDep, channel_id: uuid.UUID) -> Channel | None:
    """Get a channel if it exists, without raising an exception.

    Returns:
        Channel if found, None otherwise.
    """
    return session.exec(select(Channel).where(Channel.id == channel_id)).first()


def get_readable_channel(
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
    channel = get_channel(session, channel_id)

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
        detail="Not enough permissions",
    )


ReadableChannel = Annotated[Channel, Depends(get_readable_channel)]


def safe_get_readable_channels(
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


SafeReadableChannels = Annotated[list[Channel], Depends(safe_get_readable_channels)]


def get_editable_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_id: uuid.UUID,
) -> Channel:
    """Retrieve a channel by ID if it can be edited by the current user.

    A channel is editable if any of the following conditions are met:
    - The channel belongs to the current user.
    - The current user is a superuser.

    Raises:
        HTTPException: If the user does not have permission to edit the channel.
    """
    channel = get_channel(session, channel_id)

    if not _can_edit_channel(channel, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions",
        )

    return channel


EditableChannel = Annotated[Channel, Depends(get_editable_channel)]


def get_editable_channel_show(
    session: SessionDep,
    channel: EditableChannel,
    show_id: uuid.UUID,
) -> ChannelShow:
    """Retrieve a channel show if it can be edited by the current user.

    Raises:
        HTTPException: 404 if the show is not found on the channel.
            Permission to edit the channel is checked by the EditableChannel dependency.
    """
    if not (channel_show := ChannelShow.get(session, channel, show_id)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Show was not found on channel",
        )

    return channel_show


EditableChannelShow = Annotated[ChannelShow, Depends(get_editable_channel_show)]


def _can_edit_channel(channel: Channel, user: CurrentUser) -> bool:
    """Check if a user has edit access to a channel."""
    return user.is_superuser or channel.user_id == user.id


def _can_read_channel(channel: Channel, user: OptionalUser) -> bool:
    """Check if a user has read access to a channel."""
    if channel.public:
        return True
    if not user:
        return False
    return user.is_superuser or channel.user_id == user.id
