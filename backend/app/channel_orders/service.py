# TODO: Validate
from sqlalchemy import case
from sqlmodel import Session, col, select

from app.channel_orders.models import ChannelOrder
from app.channel_orders.schemas import (
    ChannelOrderAdminListOutput,
    ChannelOrderAdminOutput,
    ChannelOrderOutput,
    ChannelOrderPublicListOutput,
    ChannelOrderPublicOutput,
)
from app.models import Visibility
from app.schemas import AdminScope, ReadOptions, ScopedReadOptions
from app.service import get_read_results
from app.users.models import User


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
) -> ChannelOrderPublicOutput:
    anonymous = order.anonymous
    return ChannelOrderPublicOutput(
        id=order.id,
        user_id=None if anonymous else order.user_id,
        name=order.name,
        description=order.description,
        visibility=order.visibility,
        anonymous=anonymous,
        config=order.config,
        icon=order.icon,
        username=None if anonymous else username,
    )


def featured_channel_orders(
    session: Session,
) -> list[ChannelOrderPublicOutput]:
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


def public_channel_order_list_output(
    session: Session,
    viewer: User | None,
    read_options: ReadOptions,
) -> ChannelOrderPublicListOutput:
    username_column = case(
        (col(ChannelOrder.anonymous).is_(True), None),
        else_=User.username,
    )
    base = (
        select(ChannelOrder)
        .join(User)
        .where(ChannelOrder.visibility == Visibility.public)
    )
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=ChannelOrderOutput,
        default_sort=ChannelOrder.created_at,
        tiebreaker=ChannelOrder.id,
        params=read_options,
        current_user=viewer,
        extra_columns={"username": username_column},
    )
    return ChannelOrderPublicListOutput(
        data=[
            public_channel_order_output(order, order.user.username) for order in rows
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


def admin_channel_order_output(
    order: ChannelOrder,
    username: str | None,
) -> ChannelOrderAdminOutput:
    return ChannelOrderAdminOutput.model_validate(order, update={"username": username})


def admin_channel_order_list_output(
    session: Session,
    viewer: User | None,
    read_options: ScopedReadOptions,
) -> ChannelOrderAdminListOutput:
    """List `ChannelOrder`s for the requested scope, regardless of visibility."""
    base = select(ChannelOrder).join(User)
    if read_options.scope == AdminScope.mine and viewer:
        base = base.where(ChannelOrder.user_id == viewer.id)
    elif read_options.scope == AdminScope.public:
        base = base.where(ChannelOrder.visibility == Visibility.public)
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        base,
        schema=ChannelOrderOutput,
        default_sort=ChannelOrder.created_at,
        tiebreaker=ChannelOrder.id,
        params=read_options,
        current_user=viewer,
        extra_columns={"username": User.username, "score": ChannelOrder.score},
    )
    return ChannelOrderAdminListOutput(
        data=[admin_channel_order_output(order, order.user.username) for order in rows],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )
