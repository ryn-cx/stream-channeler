# TODO: Validate
"""Channel dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import select

from app.auth.dependencies import SessionDep
from app.channels.models import Channel, ChannelQueue, ChannelShow
from app.media.service import editable_record, existing_record, readable_record


# A channel holds a canonical show rather than any one website's row for it, so
# the row on the channel is named by the canonical show and nothing else. A row a
# website filed two shows under stands for each of them, and naming the channel's
# entry by it would leave the two entries indistinguishable.
# TODO: Validate
def _require_owned_channel_canonical_show(
    session: SessionDep,
    channel: EditableChannel,
    canonical_show_id: uuid.UUID,
) -> ChannelShow:
    channel_show = session.exec(
        select(ChannelShow).where(
            ChannelShow.channel_id == channel.id,
            ChannelShow.canonical_show_id == canonical_show_id,
        ),
    ).first()
    if channel_show is None:
        raise HTTPException(status_code=404, detail="Show was not found on channel")
    return channel_show


# Reading which of a title's seasons and episodes a channel carries says no more
# than watching the channel already does, so it is gated on the channel being the
# viewer's to see rather than theirs to edit. Setting the filters stays with
# `EditableChannelCanonicalShow`.
# TODO: Validate
def _require_readable_channel_canonical_show(
    session: SessionDep,
    channel: ReadableChannel,
    canonical_show_id: uuid.UUID,
) -> ChannelShow:
    channel_show = session.exec(
        select(ChannelShow).where(
            ChannelShow.channel_id == channel.id,
            ChannelShow.canonical_show_id == canonical_show_id,
        ),
    ).first()
    if channel_show is None:
        raise HTTPException(status_code=404, detail="Show was not found on channel")
    return channel_show


# A queue entry is named by its own id, but it is reached through the channel it
# is queued on, so it is only found where that channel is the one it belongs to.
# TODO: Validate
def _require_channel_queue_entry(
    session: SessionDep,
    channel: EditableChannel,
    url_id: uuid.UUID,
) -> ChannelQueue:
    queue_entry = session.exec(
        select(ChannelQueue).where(
            ChannelQueue.channel_id == channel.id,
            ChannelQueue.id == url_id,
        ),
    ).first()
    if queue_entry is None:
        raise HTTPException(status_code=404, detail="URL not found")
    return queue_entry


# The admin routes reach a queue entry by its id alone, since an admin is not
# working through any one channel.
# TODO: Validate
def _require_queue_entry(session: SessionDep, queue_id: uuid.UUID) -> ChannelQueue:
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if queue_entry is None:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    return queue_entry


EditableChannelCanonicalShow = Annotated[
    ChannelShow,
    Depends(_require_owned_channel_canonical_show),
]
EditableChannelQueueEntry = Annotated[
    ChannelQueue,
    Depends(_require_channel_queue_entry),
]
ExistingChannelQueueEntry = Annotated[ChannelQueue, Depends(_require_queue_entry)]
ReadableChannelCanonicalShow = Annotated[
    ChannelShow,
    Depends(_require_readable_channel_canonical_show),
]
EditableChannel = Annotated[Channel, Depends(editable_record(Channel, "channel_id"))]
ReadableChannel = Annotated[Channel, Depends(readable_record(Channel, "channel_id"))]
ExistingChannel = Annotated[Channel, Depends(existing_record(Channel, "channel_id"))]
