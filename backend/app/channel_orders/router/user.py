# TODO: Validate


import uuid

from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.channel_orders import service
from app.channel_orders.dependencies import (
    EditableChannelOrder,
    ReadableChannelOrder,
)
from app.channel_orders.models import ChannelOrder
from app.channel_orders.schemas import (
    ChannelOrderCopyInput,
    ChannelOrderCreate,
    ChannelOrderOutput,
    ChannelOrderUpdate,
)
from app.media.service import delete_record
from app.schemas import Message

channel_orders_router = APIRouter(
    prefix="/channel-orders",
    tags=["channel_orders"],
)


# TODO: Validate
@channel_orders_router.post("", response_model=ChannelOrderOutput)
def create_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order_input: ChannelOrderCreate,
) -> ChannelOrder:
    """Create a `ChannelOrder` owned by the `User`."""
    return service.create_channel_order(session, current_user, order_input)


# TODO: Validate
@channel_orders_router.get("/favorite-ids")
def get_favorite_channel_order_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[uuid.UUID]:
    """List the ids of the `ChannelOrder`s the current `User` has favorited."""
    return service.favorite_channel_order_ids(session, current_user)


# TODO: Validate
@channel_orders_router.post("/{channel_order_id}/favorite")  # noqa: FAST003 - Used by ReadableChannelOrder
def favorite_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order: ReadableChannelOrder,
) -> Message:
    """Favorite a `ChannelOrder` if it's readable by the `User`."""
    return service.favorite_channel_order(session, current_user, order)


# TODO: Validate
@channel_orders_router.delete("/{channel_order_id}/favorite")  # noqa: FAST003 - Used by ReadableChannelOrder
def unfavorite_channel_order(
    session: SessionDep,
    current_user: CurrentUser,
    order: ReadableChannelOrder,
) -> Message:
    """Remove a `ChannelOrder` from the `User`'s favorites."""
    return service.unfavorite_channel_order(session, current_user, order)


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
    return service.copy_channel_order(session, current_user, order, copy_in)


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


router = APIRouter()
router.include_router(channel_orders_router)
