# TODO: Validate


from collections.abc import Sequence

from sqlmodel import Session

from app.channels.channel_scope import (
    readable_channels,
)
from app.channels.models import (
    Channel,
    ChannelCombinedChannel,
)
from app.channels.schemas import (
    CombinedChannelInput,
    CombinedChannelOutput,
)
from app.schemas import Message
from app.users.models import User


# TODO: Validate
def set_channel_combined_channels(
    session: Session,
    channel: Channel,
    combined_channels: Sequence[CombinedChannelInput],
) -> None:
    """Replace a `Channel`s `CombinedChannel`s with the given channels."""
    unique = {
        combined.id: combined
        for combined in combined_channels
        if combined.id != channel.id
    }
    channel.combined_channels = [
        ChannelCombinedChannel(
            channel_id=channel.id,
            combined_channel_id=combined.id,
        )
        for combined in unique.values()
    ]
    session.commit()


# TODO: Validate
def combined_channels_output(
    channel: Channel,
    session: Session,
) -> list[CombinedChannelOutput]:
    """Return a `Channel`'s `CombinedChannel`s."""
    result: list[CombinedChannelOutput] = []
    for combined in channel.combined_channels:
        combined_channel = session.get(Channel, combined.combined_channel_id)
        result.append(
            CombinedChannelOutput(
                id=combined.combined_channel_id,
                name=combined_channel.name if combined_channel else None,
            ),
        )
    return result


# TODO: Validate
def replace_combined_channels(
    session: Session,
    current_user: User,
    channel: Channel,
    combined_channels: list[CombinedChannelInput],
) -> Message:
    """Replace a `Channel`'s `CombinedChannel`s."""
    readable_ids = {
        readable.id
        for readable in readable_channels(
            session,
            current_user,
            [combined.id for combined in combined_channels],
        )
    }
    readable = [
        combined for combined in combined_channels if combined.id in readable_ids
    ]
    set_channel_combined_channels(session, channel, readable)
    return Message(message="Combined channels updated successfully")
