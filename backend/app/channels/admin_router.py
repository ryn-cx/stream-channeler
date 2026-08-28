# TODO: Validate


import uuid

from fastapi import APIRouter, Depends

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
    return service.admin_update_channel_output(session, channel, channel_in)


# TODO: Validate
@admin_router.get("/queue")
def get_all_channel_queues(
    session: SessionDep,
    current_user: SuperUser,
    owner: MediaOwner | None = None,
) -> list[ChannelQueueAdminOutput]:
    """List every `Channel`'s import queue entries, scoped by owner."""
    return service.all_channel_queues(session, current_user, owner)


# TODO: Validate
@admin_router.patch("/queue/{queue_id}")
def admin_update_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    return service.admin_update_channel_queue(session, queue_id, queue_in)


# TODO: Validate
@admin_router.delete("/queue/{queue_id}")
def admin_delete_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
) -> Message:
    """Delete a `Channel`'s queue entry as an admin."""
    return service.admin_delete_channel_queue(session, queue_id)


router = APIRouter()


router.include_router(admin_router)
