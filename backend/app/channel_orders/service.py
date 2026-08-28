# TODO: Validate
import uuid

from sqlmodel import Session, col, select

from app.channel_orders.models import ChannelOrder, ChannelOrderFavorite
from app.channel_orders.schemas import (
    ChannelOrderAdminUpdate,
    ChannelOrderCopyInput,
    ChannelOrderCreate,
    ChannelOrderListOutput,
    ChannelOrderOutput,
    ChannelOrdersPublic,
)
from app.models import Visibility
from app.schemas import Message, ScopedReadOptions
from app.service import scoped_list_response
from app.users.models import User


# TODO: Validate
def scoped_channel_order_list_output(
    session: Session,
    viewer: User | None,
    read_options: ScopedReadOptions,
) -> ChannelOrdersPublic:
    """List `ChannelOrder`s for the requested scope."""
    return scoped_list_response(
        session=session,
        model=ChannelOrder,
        viewer=viewer,
        read_options=read_options,
        schema=ChannelOrderListOutput,
        response_model=ChannelOrdersPublic,
        favorite_model=ChannelOrderFavorite,
        favorite_record_id=ChannelOrderFavorite.channel_order_id,
    )


# TODO: Validate
def channel_order_output(
    order: ChannelOrder,
    viewer: User | None,
) -> ChannelOrderOutput:
    output = ChannelOrderOutput.model_validate(order)
    if not order.anonymous:
        return output
    if viewer and (viewer.is_superuser or viewer.id == order.user_id):
        return output
    output.user_id = None
    return output


# TODO: Validate
def public_channel_order_output(
    order: ChannelOrder,
    username: str | None,
) -> ChannelOrderListOutput:
    anonymous = order.anonymous
    return ChannelOrderListOutput(
        id=order.id,
        user_id=None if anonymous else order.user_id,
        name=order.name,
        description=order.description,
        visibility=order.visibility,
        anonymous=anonymous,
        config=order.config,
        icon=order.icon,
        username=None if anonymous else username,
        score=order.score,
    )


# TODO: Validate
def featured_channel_orders(
    session: Session,
) -> list[ChannelOrderListOutput]:
    """List public `ChannelOrder`s with a positive score, highest score first."""
    rows = session.exec(
        select(ChannelOrder)
        .where(
            ChannelOrder.visibility == Visibility.public,
            ChannelOrder.score >= 1,
        )
        .order_by(
            col(ChannelOrder.score).desc(),
            col(ChannelOrder.name),
            col(ChannelOrder.id),
        ),
    ).all()
    return [public_channel_order_output(order, order.user.username) for order in rows]


# TODO: Validate
def admin_channel_order_output(
    order: ChannelOrder,
    username: str | None,
) -> ChannelOrderListOutput:
    return ChannelOrderListOutput.model_validate(order, update={"username": username})


# TODO: Validate
def create_channel_order(
    session: Session,
    current_user: User,
    order_input: ChannelOrderCreate,
) -> ChannelOrder:
    """Create a `ChannelOrder` owned by the `User`."""
    order = ChannelOrder.model_validate(
        order_input,
        update={"user_id": current_user.id},
    )
    session.add(order)
    session.commit()
    session.refresh(order)
    return order


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


# TODO: Validate
def copy_channel_order(
    session: Session,
    current_user: User,
    order: ChannelOrder,
    copy_in: ChannelOrderCopyInput,
) -> ChannelOrder:
    """Copy a readable `ChannelOrder` into the current `User`'s account."""
    fallback_name = f"Copy of {order.name}" if order.name else "Copied order"
    new_order = ChannelOrder(
        name=copy_in.name or fallback_name,
        description=order.description,
        visibility=Visibility.private,
        anonymous=False,
        config=order.config,
        icon=order.icon,
        user_id=current_user.id,
    )
    session.add(new_order)
    session.commit()
    session.refresh(new_order)
    return new_order


# TODO: Validate
def admin_update_channel_order(
    session: Session,
    order: ChannelOrder,
    order_in: ChannelOrderAdminUpdate,
) -> ChannelOrderListOutput:
    """Update any field on any `ChannelOrder` as an admin, including `score`."""
    order.sqlmodel_update(order_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(order)
    username = session.get_one(User, order.user_id).username
    return admin_channel_order_output(order, username)
