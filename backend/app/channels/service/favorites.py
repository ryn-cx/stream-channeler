# TODO: Validate


import uuid

from sqlmodel import Session, select

from app.channels.models import (
    Channel,
    ChannelFavorite,
)
from app.channels.schemas import (
    ChannelFavoriteUpdate,
)
from app.schemas import Message
from app.users.models import User


# TODO: Validate
def favorite_channel(
    session: Session,
    current_user: User,
    channel: Channel,
) -> Message:
    """Favorite a `Channel` if it's readable by the `User`."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        session.add(ChannelFavorite(user_id=current_user.id, channel_id=channel.id))
        session.commit()
    return Message(message="Channel favorited successfully")


# TODO: Validate
def update_channel_favorite(
    session: Session,
    current_user: User,
    channel: Channel,
    favorite_in: ChannelFavoriteUpdate,
) -> Message:
    """Set the `User`'s private name/number for a favorited `Channel`.

    Favoriting the channel first if it isn't already, so personalizing it from the
    favorites view can never race against the favorite not yet existing.
    """
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        favorite = ChannelFavorite(user_id=current_user.id, channel_id=channel.id)
        session.add(favorite)
    favorite.name = favorite_in.name
    favorite.channel_number = favorite_in.channel_number
    session.commit()
    return Message(message="Favorite updated successfully")


# TODO: Validate
def unfavorite_channel(
    session: Session,
    current_user: User,
    channel: Channel,
) -> Message:
    """Remove a `Channel` from the `User`'s favorites."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is not None:
        session.delete(favorite)
        session.commit()
    return Message(message="Channel unfavorited successfully")


# TODO: Validate
def favorite_channel_ids(session: Session, current_user: User) -> list[uuid.UUID]:
    """List the ids of the `Channel`s the current `User` has favorited.

    Unreadable favorites are left in because this only drives the favorite toggle;
    the `favorites` scope of the list endpoint is what applies the read rules.
    """
    return list(
        session.exec(
            select(ChannelFavorite.channel_id).where(
                ChannelFavorite.user_id == current_user.id,
            ),
        ).all(),
    )
