# TODO: Validate


import uuid
from collections.abc import Sequence
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlmodel import Session, col, select

from app.channels.models import (
    Channel,
    ChannelQueue,
    URLStatus,
)
from app.channels.schemas import (
    ChannelQueueAdminOutput,
    ChannelQueueAdminUpdate,
    MediaOwner,
)
from app.schemas import Message
from app.users.models import User
from app.users.service import get_or_create_plugin_user
from app.utils import tz_datetime


# TODO: Validate
def _unique_urls(urls: Sequence[str]) -> list[str]:
    """Remove duplicate URLs without changing the order."""
    return list(dict.fromkeys(url.strip() for url in urls))


# TODO: Validate
def _write_queue_rows(
    session: Session,
    channel: Channel,
    urls: Sequence[str],
) -> None:
    """Add URLs into a channel's import queue as fast as possible."""
    unique_urls = _unique_urls(urls)

    timestamp = tz_datetime.current_time()

    # When an existing URL is re-added to the queue, it is reset to pending because the
    # user may have removed it from the channel or it may have failed to import for some
    # reason.
    statement = postgres_insert(ChannelQueue).on_conflict_do_update(
        index_elements=["channel_id", "url"],
        set_={"status": URLStatus.PENDING, "modified_at": timestamp},
    )
    session.connection().execute(
        statement,
        [
            {
                "id": uuid.uuid4(),
                "channel_id": channel.id,
                "url": url,
                "status": URLStatus.PENDING,
                # The queue is read newest first, so every row of a batch gets a
                # timestamp of its own to keep the input order readable.
                "created_at": timestamp + timedelta(microseconds=index),
                "modified_at": timestamp + timedelta(microseconds=index),
            }
            for index, url in enumerate(unique_urls)
        ],
    )


# TODO: Validate
def add_urls_to_channel_import_queue(
    session: Session,
    channel: Channel,
    urls: Sequence[str],
) -> None:
    _write_queue_rows(session, channel, urls)
    session.commit()


# TODO: Validate
def bulk_import_queue_urls(
    session: Session,
    current_user: User,
    entries: dict[uuid.UUID, list[str]],
) -> Message:
    """Add URLs to multiple channels' import queues at once."""
    channels_by_id = {
        channel.id: channel
        for channel in session.exec(
            select(Channel)
            .where(col(Channel.id).in_(entries.keys()))
            .where(Channel.user_id == current_user.id),
        ).all()
    }
    total_urls = 0
    queue_entries: list[tuple[Channel, Sequence[str]]] = []
    for channel_id, urls in entries.items():
        if channel := channels_by_id.get(channel_id):
            queue_entries.append((channel, urls))
            total_urls += len(urls)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel {channel_id} not found",
            )

    for entry_channel, entry_urls in queue_entries:
        _write_queue_rows(session, entry_channel, entry_urls)
    session.commit()
    return Message(message=f"{total_urls} URLs added across {len(entries)} channels")


# TODO: Validate
def channel_queue(
    session: Session,
    channel: Channel,
) -> list[ChannelQueue]:
    """Read the URLs in a channel's import queue."""
    statement = (
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        # Descending order works better on the frontend because new URLs are appended to the
        # top of the list making it possible to immediately see the new URLs after adding
        # them without having to scroll down.
        .order_by(col(ChannelQueue.created_at).desc())
    )

    channels = session.exec(statement).all()

    return list(channels)


# TODO: Validate
def delete_queue_entry(session: Session, queue_entry: ChannelQueue) -> Message:
    """Delete one entry from a channel's import queue."""
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


# TODO: Validate
def clear_completed_queue(
    session: Session,
    channel: Channel,
) -> Message:
    """Clear a channel's import queue."""
    for queue_entry in channel.queue:
        if queue_entry.status == URLStatus.IMPORTED:
            session.delete(queue_entry)

    session.commit()
    return Message(message="Import queue cleared successfully")


# TODO: Validate
def _channel_queue_admin_output(
    channel: Channel,
    username: str | None,
    queue_entry: ChannelQueue,
) -> ChannelQueueAdminOutput:
    return ChannelQueueAdminOutput.model_validate(
        queue_entry,
        update={
            "channel_name": channel.name,
            "channel_number": channel.channel_number,
            "user_id": channel.user_id,
            "username": username,
        },
    )


# TODO: Validate
def all_channel_queues(
    session: Session,
    current_user: User,
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
    return [
        _channel_queue_admin_output(channel, username, queue_entry)
        for queue_entry, channel, username in session.exec(selector).all()
    ]


# TODO: Validate
def admin_update_channel_queue(
    session: Session,
    queue_entry: ChannelQueue,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    queue_entry.sqlmodel_update(queue_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(queue_entry)
    channel = session.get_one(Channel, queue_entry.channel_id)
    username = session.get_one(User, channel.user_id).username
    return _channel_queue_admin_output(channel, username, queue_entry)
