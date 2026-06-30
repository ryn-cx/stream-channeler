# TODO: Validate
"""Channel dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException

from app.auth.dependencies import SessionDep
from app.channels.models import Channel, ChannelShow
from app.media.service import existing_record, owned_record, readable_record
from app.shows.dependencies import ReadableShow


def _require_owned_channel_readable_show(
    session: SessionDep,
    channel: OwnedChannel,
    show: ReadableShow,
) -> ChannelShow:
    if channel_show := ChannelShow.get(session, channel, show):
        return channel_show
    raise HTTPException(status_code=404, detail="Show was not found on channel")


OwnedChannelReadableShow = Annotated[
    ChannelShow,
    Depends(_require_owned_channel_readable_show),
]
OwnedChannel = Annotated[Channel, Depends(owned_record(Channel, "channel_id"))]
ReadableChannel = Annotated[Channel, Depends(readable_record(Channel, "channel_id"))]
ExistingChannel = Annotated[Channel, Depends(existing_record(Channel, "channel_id"))]
