# TODO: Validate
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    get_current_active_superuser,
)
from app.channel_orders import service
from app.channel_orders.dependencies import (
    EditableChannelOrder,
    ExistingChannelOrder,
    ReadableChannelOrder,
)
from app.channel_orders.models import ChannelOrder, ChannelOrderFavorite
from app.channel_orders.schemas import (
    ChannelOrderAdminUpdate,
    ChannelOrderCopyInput,
    ChannelOrderCreate,
    ChannelOrderListOutput,
    ChannelOrderOutput,
    ChannelOrderReadOptions,
    ChannelOrdersPublic,
    ChannelOrderUpdate,
)
from app.media.service import delete_record
from app.models import Visibility
from app.schemas import Message
from app.users.dependencies import OptionalUser
from app.users.models import User

channel_orders_router = APIRouter(
    prefix="/channel-orders",
    tags=["channel_orders"],
)
admin_channel_orders_router = APIRouter(
    prefix="/admin/channel-orders",
    tags=["channel_orders"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@channel_orders_router.post("", response_model=ChannelOrderOutput)
def create_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
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
@channel_orders_router.get("")
def get_channel_orders(
    session: SessionDep,
    current_user: OptionalUser,
    read_options: Annotated[ChannelOrderReadOptions, Query()],
) -> ChannelOrdersPublic:
    """Get `ChannelOrder`s."""
    return service.scoped_channel_order_list_output(session, current_user, read_options)


# TODO: Validate
@channel_orders_router.get("/featured")
def get_featured_channel_orders(
    session: SessionDep,
) -> list[ChannelOrderListOutput]:
    """List public `ChannelOrder`s with a positive score for onboarding."""
    return service.featured_channel_orders(session)


# TODO: Validate
@channel_orders_router.get("/favorite-ids")
def get_favorite_channel_order_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[uuid.UUID]:
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
@channel_orders_router.post("/{channel_order_id}/favorite")  # noqa: FAST003 - Used by ReadableChannelOrder
def favorite_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order: ReadableChannelOrder,
) -> Message:
    """Favorite a `ChannelOrder` if it's readable by the `User`."""
    favorite = session.get(ChannelOrderFavorite, (current_user.id, order.id))
    if favorite is None:
        session.add(
            ChannelOrderFavorite(user_id=current_user.id, channel_order_id=order.id),
        )
        session.commit()
    return Message(message="Order favorited successfully")


# TODO: Validate
@channel_orders_router.delete("/{channel_order_id}/favorite")  # noqa: FAST003 - Used by ReadableChannelOrder
def unfavorite_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order: ReadableChannelOrder,
) -> Message:
    """Remove a `ChannelOrder` from the `User`'s favorites."""
    favorite = session.get(ChannelOrderFavorite, (current_user.id, order.id))
    if favorite is not None:
        session.delete(favorite)
        session.commit()
    return Message(message="Order unfavorited successfully")


# TODO: Validate
@channel_orders_router.post(
    "/{channel_order_id}/copy",  # noqa: FAST003 - Used by ReadableChannelOrder
    response_model=ChannelOrderOutput,
)
def copy_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order: ReadableChannelOrder,
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
@channel_orders_router.get("/{channel_order_id}", response_model=ChannelOrderOutput)  # noqa: FAST003 - Used by ReadableChannelOrder
def get_channel_order(
    order: ReadableChannelOrder,
    optional_user: OptionalUser,
) -> ChannelOrderOutput:
    """Return a `ChannelOrder` if it's readable by the `User`."""
    return service.channel_order_output(order, optional_user)


# TODO: Validate
@channel_orders_router.patch("/{channel_order_id}", response_model=ChannelOrderOutput)  # noqa: FAST003 - Used by EditableChannelOrder
def update_channel_order(
    session: SessionDep,
    order: EditableChannelOrder,
    order_in: ChannelOrderUpdate,
) -> ChannelOrder:
    """Update and return a `ChannelOrder` if it's editable by the `User`."""
    return order_in.update(session, order)


# TODO: Validate
@channel_orders_router.delete("/{channel_order_id}")  # noqa: FAST003 - Used by EditableChannelOrder
def delete_channel_order(
    session: SessionDep,
    order: EditableChannelOrder,
) -> Message:
    """Delete a `ChannelOrder` if it's editable by the `User`."""
    return delete_record(session, order)


# TODO: Validate
@admin_channel_orders_router.patch("/{channel_order_id}")  # noqa: FAST003 - Used by ExistingChannelOrder
def admin_update_channel_order(
    session: SessionDep,
    order: ExistingChannelOrder,
    order_in: ChannelOrderAdminUpdate,
) -> ChannelOrderListOutput:
    """Update any field on any `ChannelOrder` as an admin, including `score`."""
    order.sqlmodel_update(order_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(order)
    username = session.get_one(User, order.user_id).username
    return service.admin_channel_order_output(order, username)


router = APIRouter()
router.include_router(channel_orders_router)
router.include_router(admin_channel_orders_router)
