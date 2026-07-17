# TODO: Validate
from sqlmodel import Session, col, select

from app.channel_orders.models import ChannelOrder, ChannelOrderFavorite
from app.channel_orders.schemas import (
    ChannelOrderListOutput,
    ChannelOrderOutput,
    ChannelOrdersPublic,
)
from app.models import Visibility
from app.schemas import ScopedReadOptions
from app.service import scoped_list_response
from app.users.models import User


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


def admin_channel_order_output(
    order: ChannelOrder,
    username: str | None,
) -> ChannelOrderListOutput:
    return ChannelOrderListOutput.model_validate(order, update={"username": username})
