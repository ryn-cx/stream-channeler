# TODO: Validate


from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    SessionDep,
)
from app.channel_orders import service
from app.channel_orders.dependencies import (
    ReadableChannelOrder,
)
from app.channel_orders.schemas import (
    ChannelOrderListOutput,
    ChannelOrderOutput,
    ChannelOrderReadOptions,
    ChannelOrdersPublic,
)
from app.users.dependencies import OptionalUser

channel_orders_router = APIRouter(
    prefix="/channel-orders",
    tags=["channel_orders"],
)


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
@channel_orders_router.get("/{channel_order_id}", response_model=ChannelOrderOutput)  # noqa: FAST003 - Used by ReadableChannelOrder
def get_channel_order(
    order: ReadableChannelOrder,
    optional_user: OptionalUser,
) -> ChannelOrderOutput:
    """Return a `ChannelOrder` if it's readable by the `User`."""
    return service.channel_order_output(order, optional_user)


router = APIRouter()
router.include_router(channel_orders_router)
