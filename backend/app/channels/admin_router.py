# TODO: Validate


import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import col, select

from app.auth.dependencies import (
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.channels import service
from app.channels.dependencies import (
    ExistingChannel,
)
from app.channels.models import (
    Channel,
    ChannelQueue,
)
from app.channels.schemas import (
    ChannelAdminCreate,
    ChannelAdminUpdate,
    ChannelListOutput,
    ChannelOutput,
    ChannelQueueAdminOutput,
    ChannelQueueAdminUpdate,
    MediaOwner,
)
from app.channels.service import (
    _channel_queue_admin_output,
)
from app.schemas import Message
from app.users.models import User
from app.users.service import get_or_create_plugin_user

admin_router = APIRouter(
    prefix="/admin/channels",
    tags=["channels"],
    dependencies=[Depends(get_current_active_superuser)],
)


# TODO: Validate
@admin_router.post("", response_model=ChannelOutput)
def admin_create_channel(
    session: SessionDep,
    channel_in: ChannelAdminCreate,
) -> Channel:
    """Create a `Channel` owned by any `User`, with its `score`, as an admin."""
    return service.admin_create_channel(session, channel_in)


# TODO: Validate
@admin_router.patch(
    "/{channel_id}",  # noqa: FAST003 - Used by ExistingChannel.
)
def admin_update_channel(
    session: SessionDep,
    channel: ExistingChannel,
    channel_in: ChannelAdminUpdate,
) -> ChannelListOutput:
    """Update any field on any `Channel` as an admin, including `score`."""
    channel = service.admin_update_channel(session, channel, channel_in)
    username = session.get_one(User, channel.user_id).username
    favorite_counts = service.channel_favorite_counts(session, [channel.id])
    return ChannelListOutput.model_validate(
        channel,
        update={
            "username": username,
            "favorite_count": favorite_counts.get(channel.id, 0),
        },
    )


# TODO: Validate
@admin_router.get("/queue")
def get_all_channel_queues(
    session: SessionDep,
    current_user: SuperUser,
    owner: MediaOwner | None = None,
) -> list[ChannelQueueAdminOutput]:
    """List every `Channel`'s import queue entries, scoped by owner."""
    selector = (
        select(ChannelQueue, Channel, User.username)
        .join(Channel, col(Channel.id) == ChannelQueue.channel_id)
        .join(User, col(User.id) == Channel.user_id)
        .order_by(col(ChannelQueue.created_at).desc())
    )
    if not owner:
        selector = selector.where(Channel.user_id == current_user.id)
    else:
        plugin_user = get_or_create_plugin_user(session=session)
        if owner == MediaOwner.official:
            selector = selector.where(Channel.user_id == plugin_user.id)
        else:
            selector = selector.where(
                col(Channel.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows = session.exec(selector).all()
    return [
        _channel_queue_admin_output(channel, username, queue_entry)
        for queue_entry, channel, username in rows
    ]


# TODO: Validate
@admin_router.patch("/queue/{queue_id}")
def admin_update_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    queue_entry.sqlmodel_update(queue_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(queue_entry)
    channel = session.get_one(Channel, queue_entry.channel_id)
    username = session.get_one(User, channel.user_id).username
    return _channel_queue_admin_output(channel, username, queue_entry)


# TODO: Validate
@admin_router.delete("/queue/{queue_id}")
def admin_delete_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
) -> Message:
    """Delete a `Channel`'s queue entry as an admin."""
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


router = APIRouter()


router.include_router(admin_router)
