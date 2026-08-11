# TODO: Validate
"""Channel dependencies."""

from typing import Annotated

from fastapi import Depends, HTTPException

from app.auth.dependencies import SessionDep
from app.channels.models import Channel, ChannelShow
from app.media.service import editable_record, existing_record, readable_record
from app.shows.dependencies import ReadableShow


# TODO: Validate
def _require_owned_channel_readable_show(
    session: SessionDep,
    channel: EditableChannel,
    show: ReadableShow,
) -> ChannelShow:
    if channel_show := ChannelShow.get(session, channel, show):
        return channel_show
    raise HTTPException(status_code=404, detail="Show was not found on channel")


EditableChannelReadableShow = Annotated[
    ChannelShow,
    Depends(_require_owned_channel_readable_show),
]
EditableChannel = Annotated[Channel, Depends(editable_record(Channel, "channel_id"))]
ReadableChannel = Annotated[Channel, Depends(readable_record(Channel, "channel_id"))]
ExistingChannel = Annotated[Channel, Depends(existing_record(Channel, "channel_id"))]
