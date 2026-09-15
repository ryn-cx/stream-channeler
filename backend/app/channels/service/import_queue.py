# TODO: Validate


import uuid
from collections.abc import Sequence
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy.dialects.postgresql import insert as postgres_insert
from sqlmodel import Session, col, func, select, update

from app.channels.models import (
    Channel,
    ChannelQueue,
    URLStatus,
)
from app.channels.schemas import (
    ChannelQueueAdminOutput,
    ChannelQueueAdminReadOptions,
    ChannelQueueAdminUpdate,
    ChannelQueueOutput,
    ChannelQueuePage,
    ChannelQueuesAdminPublic,
    MediaOwner,
)
from app.schemas import Message
from app.service.responses import get_read_results
from app.users.models import User
from app.users.plugin_user import is_plugin_user
from app.utils import tz_datetime

CHANNEL_QUEUE_PAGE = 25


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
    if not unique_urls:
        return

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
    offset: int = 0,
    limit: int = CHANNEL_QUEUE_PAGE,
    query: str | None = None,
) -> ChannelQueuePage:
    """Read the URLs in a channel's import queue."""
    matching = select(ChannelQueue).where(ChannelQueue.channel_id == channel.id)
    if query:
        matching = matching.where(col(ChannelQueue.url).icontains(query))

    statement = (
        matching
        # Descending order works better on the frontend because new URLs are appended to the
        # top of the list making it possible to immediately see the new URLs after adding
        # them without having to scroll down.
        .order_by(col(ChannelQueue.created_at).desc())
        .offset(offset)
        .limit(limit)
    )

    total = session.scalar(
        select(func.count()).select_from(matching.subquery()),
    )
    # The tab's badge counts what the queue still has to do, which is every
    # unfinished entry rather than only the ones the page being read shows.
    pending_count = session.scalar(
        select(func.count())
        .select_from(ChannelQueue)
        .where(
            ChannelQueue.channel_id == channel.id,
            col(ChannelQueue.status).in_([URLStatus.PENDING, URLStatus.IMPORTING]),
        ),
    )

    return ChannelQueuePage(
        data=[
            ChannelQueueOutput.model_validate(queue_entry)
            for queue_entry in session.exec(statement).all()
        ],
        total=total or 0,
        pending_count=pending_count or 0,
    )


# TODO: Validate
def retry_queue_entry(session: Session, queue_entry: ChannelQueue) -> Message:
    """Put one entry back into a channel's import queue to be imported again."""
    queue_entry.status = URLStatus.PENDING
    queue_entry.note = None
    # A plugin that pushed the import out to a later time was answering the failure
    # this retry is discarding, so the entry goes back to being importable now.
    queue_entry.import_at = None
    session.add(queue_entry)
    session.commit()
    return Message(message=f"{queue_entry.url} queued for import again")


# TODO: Validate
def retry_failed_queue_entries(session: Session, channel: Channel) -> Message:
    result = session.exec(
        update(ChannelQueue)
        .where(
            col(ChannelQueue.channel_id) == channel.id,
            col(ChannelQueue.status) == URLStatus.FAILED,
        )
        .values(
            status=URLStatus.PENDING,
            note=None,
            # A plugin that pushed the import out to a later time was answering the
            # failure this retry is discarding, so the entry goes back to being
            # importable now.
            import_at=None,
            modified_at=tz_datetime.current_time(),
        ),
    )
    session.commit()
    return Message(message=f"{result.rowcount} URLs queued for import again")


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
    read_options: ChannelQueueAdminReadOptions,
) -> ChannelQueuesAdminPublic:
    """List every `Channel`'s import queue entries, scoped by owner."""
    selector = (
        select(ChannelQueue)
        .join(Channel, col(Channel.id) == ChannelQueue.channel_id)
        .join(User, col(User.id) == Channel.user_id)
    )
    if read_options.owner == MediaOwner.official:
        selector = selector.where(is_plugin_user(User.email))
    elif read_options.owner == MediaOwner.others:
        selector = selector.where(
            ~is_plugin_user(User.email),
            col(Channel.user_id) != current_user.id,
        )
    rows, total_count, filtered_count, is_server_side = get_read_results(
        session,
        selector,
        schema=ChannelQueueAdminOutput,
        default_sorts=[ChannelQueue.created_at],
        tiebreaker=ChannelQueue.id,
        params=read_options,
        current_user=current_user,
        extra_columns={
            "channel_name": Channel.name,
            "channel_number": Channel.channel_number,
            "user_id": Channel.user_id,
            "username": User.username,
        },
    )
    owners = {
        channel.id: (channel, username)
        for channel, username in session.exec(
            select(Channel, User.username)
            .join(User, col(User.id) == Channel.user_id)
            .where(col(Channel.id).in_({row.channel_id for row in rows})),
        ).all()
    }
    return ChannelQueuesAdminPublic(
        data=[
            _channel_queue_admin_output(*owners[row.channel_id], row) for row in rows
        ],
        total_count=total_count,
        filtered_count=filtered_count,
        is_server_side=is_server_side,
    )


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
