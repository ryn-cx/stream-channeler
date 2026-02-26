# TODO: Validate
import uuid
from collections.abc import Sequence

from fastapi import HTTPException, status
from sqlmodel import Session

from app.auth.dependencies import CurrentUser
from app.channels.models import Channel, ChannelQueue, URLStatus
from app.channels.schemas import ChannelInput, ChannelQueueInput


def create_channel(
    session: Session,
    user_id: uuid.UUID,
    channel_in: ChannelInput,
) -> Channel:
    if Channel.get(session, user_id, channel_in.name):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Channel with this name already exists",
        )
    channel = Channel.model_validate(channel_in, update={"user_id": user_id})
    session.add(channel)
    session.commit()
    session.refresh(channel)
    return channel


def update_channel(
    session: Session,
    current_user: CurrentUser,
    channel_in: ChannelInput,
    channel: Channel,
) -> Channel:
    for existing_channel in current_user.channels:
        if (
            existing_channel.name == channel_in.name
            and existing_channel.id != channel.id
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Channel with this name already exists",
            )

    update_dict = channel_in.model_dump(exclude_unset=True)
    channel.sqlmodel_update(update_dict)
    session.add(channel)
    session.commit()
    session.refresh(channel)
    return channel


def add_urls_to_channel_import_queue(
    session: Session,
    channel: Channel,
    urls: Sequence[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    queue_by_url = {queue.url: queue for queue in channel.queue}

    # Remove duplicates while preserving order
    unique_urls = dict.fromkeys(urls)

    output: list[ChannelQueue] = []
    for url in unique_urls:
        stripped_url = url.strip()
        existing_queue_entry = queue_by_url.get(stripped_url)

        queue_entry = ChannelQueueInput(
            url=stripped_url,
            status=URLStatus.PENDING,
        ).upsert(channel, existing_queue_entry)

        output.append(queue_entry)

    session.commit()
    return output
