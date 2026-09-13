# TODO: Validate


import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.auth.dependencies import (
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.channels.dependencies import (
    ExistingChannel,
    ExistingChannelQueueEntry,
)
from app.channels.models import (
    Channel,
)
from app.channels.schemas import (
    AutomaticChannelUserOutput,
    ChannelAdminCreate,
    ChannelAdminUpdate,
    ChannelListOutput,
    ChannelOutput,
    ChannelQueueAdminOutput,
    ChannelQueueAdminReadOptions,
    ChannelQueueAdminUpdate,
    ChannelQueuesAdminPublic,
)
from app.channels.service import channels, import_queue
from app.schemas import Message

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
    return channels.admin_create_channel(session, channel_in)


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
    return channels.admin_update_channel_output(session, channel, channel_in)


# TODO: Validate
@admin_router.get("/automatic-users")
def get_automatic_channel_users(
    session: SessionDep,
) -> list[AutomaticChannelUserOutput]:
    """List the `User`s whose channels a source writes, and how many they hold."""
    return channels.automatic_channel_users(session)


# TODO: Validate
@admin_router.delete("/automatic-users/{user_id}")
def clear_automatic_channels(
    session: SessionDep,
    user_id: uuid.UUID,
) -> Message:
    """Empty every `Channel` an automatic channel `User` owns."""
    return channels.clear_automatic_channels(session, user_id)


# TODO: Validate
@admin_router.get("/queue")
def get_all_channel_queues(
    session: SessionDep,
    current_user: SuperUser,
    read_options: Annotated[ChannelQueueAdminReadOptions, Query()],
) -> ChannelQueuesAdminPublic:
    """List every `Channel`'s import queue entries, scoped by owner."""
    return import_queue.all_channel_queues(session, current_user, read_options)


# TODO: Validate
@admin_router.patch("/queue/{queue_id}")  # noqa: FAST003 - Used by ExistingChannelQueueEntry.
def admin_update_channel_queue(
    session: SessionDep,
    queue_entry: ExistingChannelQueueEntry,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    return import_queue.admin_update_channel_queue(session, queue_entry, queue_in)


# TODO: Validate
@admin_router.delete("/queue/{queue_id}")  # noqa: FAST003 - Used by ExistingChannelQueueEntry.
def admin_delete_channel_queue(
    session: SessionDep,
    queue_entry: ExistingChannelQueueEntry,
) -> Message:
    """Delete a `Channel`'s queue entry as an admin."""
    return import_queue.delete_queue_entry(session, queue_entry)


router = APIRouter()


router.include_router(admin_router)
