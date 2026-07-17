# TODO: Validate
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlmodel import select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.channel_orders import service
from app.channel_orders.dependencies import (
    EditableChannelOrder,
    ExistingChannelOrder,
    ReadableChannelOrder,
)
from app.channel_orders.models import ChannelOrder
from app.channel_orders.schemas import (
    ChannelOrderAdminListOutput,
    ChannelOrderAdminOutput,
    ChannelOrderAdminUpdate,
    ChannelOrderCopyInput,
    ChannelOrderCreate,
    ChannelOrderOutput,
    ChannelOrderPublicListOutput,
    ChannelOrderPublicOutput,
    ChannelOrderUpdate,
)
from app.media.service import delete_record
from app.models import Visibility
from app.schemas import Message, ReadOptions, ScopedReadOptions
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


@channel_orders_router.get("")
def get_channel_orders(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[ChannelOrderOutput]:
    """List the current `User`'s `ChannelOrder`s."""
    orders = session.exec(
        select(ChannelOrder).where(ChannelOrder.user_id == current_user.id),
    ).all()
    return [service.channel_order_output(order, current_user) for order in orders]


@channel_orders_router.get("/public")
def get_public_channel_orders(
    session: SessionDep,
    current_user: OptionalUser,
    read_options: Annotated[ReadOptions, Query()],
) -> ChannelOrderPublicListOutput:
    """List public `ChannelOrder`s, applying the viewer's server-side filtering."""
    return service.public_channel_order_list_output(
        session,
        current_user,
        read_options,
    )


@channel_orders_router.get("/featured")
def get_featured_channel_orders(
    session: SessionDep,
) -> list[ChannelOrderPublicOutput]:
    """List public `ChannelOrder`s with a positive score for onboarding."""
    return service.featured_channel_orders(session)


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


@channel_orders_router.get("/{channel_order_id}", response_model=ChannelOrderOutput)  # noqa: FAST003 - Used by ReadableChannelOrder
def get_channel_order(
    order: ReadableChannelOrder,
    optional_user: OptionalUser,
) -> ChannelOrderOutput:
    """Return a `ChannelOrder` if it's readable by the `User`."""
    return service.channel_order_output(order, optional_user)


@channel_orders_router.patch("/{channel_order_id}", response_model=ChannelOrderOutput)  # noqa: FAST003 - Used by EditableChannelOrder
def update_channel_order(
    session: SessionDep,
    order: EditableChannelOrder,
    order_in: ChannelOrderUpdate,
) -> ChannelOrder:
    """Update and return a `ChannelOrder` if it's editable by the `User`."""
    return order_in.update(session, order)


@channel_orders_router.delete("/{channel_order_id}")  # noqa: FAST003 - Used by EditableChannelOrder
def delete_channel_order(
    session: SessionDep,
    order: EditableChannelOrder,
) -> Message:
    """Delete a `ChannelOrder` if it's editable by the `User`."""
    return delete_record(session, order)


@admin_channel_orders_router.get("")
def admin_get_channel_orders(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ScopedReadOptions, Query()],
) -> ChannelOrderAdminListOutput:
    """List `ChannelOrder`s for the requested scope, regardless of visibility."""
    return service.admin_channel_order_list_output(
        session,
        current_user,
        read_options,
    )


@admin_channel_orders_router.patch("/{channel_order_id}")  # noqa: FAST003 - Used by ExistingChannelOrder
def admin_update_channel_order(
    session: SessionDep,
    order: ExistingChannelOrder,
    order_in: ChannelOrderAdminUpdate,
) -> ChannelOrderAdminOutput:
    """Update any field on any `ChannelOrder` as an admin, including `score`."""
    order.sqlmodel_update(order_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(order)
    username = session.get_one(User, order.user_id).username
    return service.admin_channel_order_output(order, username)


router = APIRouter()
router.include_router(channel_orders_router)
router.include_router(admin_channel_orders_router)
