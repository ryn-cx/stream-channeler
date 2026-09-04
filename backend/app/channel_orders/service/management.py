# TODO: Validate

from sqlmodel import Session

from app.channel_orders.models import ChannelOrder
from app.channel_orders.schemas import (
    ChannelOrderAdminUpdate,
    ChannelOrderCopyInput,
    ChannelOrderCreate,
    ChannelOrderListOutput,
)
from app.channel_orders.service.outputs import admin_channel_order_output
from app.models import Visibility
from app.users.models import User


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
