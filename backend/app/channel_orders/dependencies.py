"""Channel order dependencies."""

from typing import Annotated

from fastapi import Depends

from app.channel_orders.models import ChannelOrder
from app.media.service import editable_record, existing_record, readable_record

EditableChannelOrder = Annotated[
    ChannelOrder,
    Depends(editable_record(ChannelOrder, "channel_order_id")),
]
ReadableChannelOrder = Annotated[
    ChannelOrder,
    Depends(readable_record(ChannelOrder, "channel_order_id")),
]
ExistingChannelOrder = Annotated[
    ChannelOrder,
    Depends(existing_record(ChannelOrder, "channel_order_id")),
]
