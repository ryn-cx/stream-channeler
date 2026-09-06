# TODO: Validate
"""Channel dependencies."""

import uuid
from typing import Annotated

from fastapi import Depends, HTTPException
from sqlmodel import select

from app.auth.dependencies import SessionDep
from app.channels.models import Channel, ChannelQueue, ChannelTitle
from app.media.service.records import editable_record, existing_record, readable_record


# A channel holds a canonical title rather than any one website's row for it, so
# the row on the channel is named by the canonical title and nothing else. A row a
# website filed two titles under stands for each of them, and naming the channel's
# entry by it would leave the two entries indistinguishable.
# TODO: Validate
def _require_owned_channel_canonical_title(
    session: SessionDep,
    channel: EditableChannel,
    canonical_title_id: uuid.UUID,
) -> ChannelTitle:
    channel_title = session.exec(
        select(ChannelTitle).where(
            ChannelTitle.channel_id == channel.id,
            ChannelTitle.canonical_title_id == canonical_title_id,
        ),
    ).first()
    if channel_title is None:
        raise HTTPException(status_code=404, detail="Title was not found on channel")
    return channel_title


# Reading which of a title's seasons and episodes a channel carries says no more
# than watching the channel already does, so it is gated on the channel being the
# viewer's to see rather than theirs to edit. Setting the filters stays with
# `EditableChannelCanonicalTitle`.
# TODO: Validate
def _require_readable_channel_canonical_title(
    session: SessionDep,
    channel: ReadableChannel,
    canonical_title_id: uuid.UUID,
) -> ChannelTitle:
    channel_title = session.exec(
        select(ChannelTitle).where(
            ChannelTitle.channel_id == channel.id,
            ChannelTitle.canonical_title_id == canonical_title_id,
        ),
    ).first()
    if channel_title is None:
        raise HTTPException(status_code=404, detail="Title was not found on channel")
    return channel_title


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


EditableChannelCanonicalTitle = Annotated[
    ChannelTitle,
    Depends(_require_owned_channel_canonical_title),
]
EditableChannelQueueEntry = Annotated[
    ChannelQueue,
    Depends(_require_channel_queue_entry),
]
ExistingChannelQueueEntry = Annotated[ChannelQueue, Depends(_require_queue_entry)]
ReadableChannelCanonicalTitle = Annotated[
    ChannelTitle,
    Depends(_require_readable_channel_canonical_title),
]
EditableChannel = Annotated[Channel, Depends(editable_record(Channel, "channel_id"))]
ReadableChannel = Annotated[Channel, Depends(readable_record(Channel, "channel_id"))]
ExistingChannel = Annotated[Channel, Depends(existing_record(Channel, "channel_id"))]
