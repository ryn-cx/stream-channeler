# TODO: Validate
import uuid

from sqlmodel import Session, select

from app.channel_orders.models import ChannelOrder, ChannelOrderFavorite
from app.schemas import Message
from app.users.models import User


# TODO: Validate
def favorite_channel_order(
    session: Session,
    current_user: User,
    order: ChannelOrder,
) -> Message:
    """Favorite a `ChannelOrder`, which favoriting it twice leaves alone."""
    if session.get(ChannelOrderFavorite, (current_user.id, order.id)) is None:
        session.add(
            ChannelOrderFavorite(user_id=current_user.id, channel_order_id=order.id),
        )
        session.commit()
    return Message(message="Order favorited successfully")


# TODO: Validate
def unfavorite_channel_order(
    session: Session,
    current_user: User,
    order: ChannelOrder,
) -> Message:
    """Remove a `ChannelOrder` from the `User`'s favorites."""
    favorite = session.get(ChannelOrderFavorite, (current_user.id, order.id))
    if favorite is not None:
        session.delete(favorite)
        session.commit()
    return Message(message="Order unfavorited successfully")


# TODO: Validate
def favorite_channel_order_ids(session: Session, current_user: User) -> list[uuid.UUID]:
    """List the ids of the `ChannelOrder`s the current `User` has favorited.

    Unreadable favorites are left in because this only drives the favorite toggle;
    the `favorites` scope of the list endpoint is what applies the read rules.
    """
    return list(
        session.exec(
            select(ChannelOrderFavorite.channel_order_id).where(
                ChannelOrderFavorite.user_id == current_user.id,
            ),
        ).all(),
    )
