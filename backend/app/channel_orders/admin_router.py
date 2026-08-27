# TODO: Validate


from fastapi import APIRouter, Depends

from app.auth.dependencies import (
    SessionDep,
    get_current_active_superuser,
)
from app.channel_orders import service
from app.channel_orders.dependencies import (
    ExistingChannelOrder,
)
from app.channel_orders.schemas import (
    ChannelOrderAdminUpdate,
    ChannelOrderListOutput,
)
from app.users.models import User

admin_channel_orders_router = APIRouter(
    prefix="/admin/channel-orders",
    tags=["channel_orders"],
    dependencies=[Depends(get_current_active_superuser)],
)


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
router.include_router(admin_channel_orders_router)
