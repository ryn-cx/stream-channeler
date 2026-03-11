import uuid

from sqlmodel import Session

from app.channels.models import Channel, ChannelQueue, ChannelShow
from app.channels.schemas import ChannelOutput
from app.plugins.models import Plugin
from app.shows.models import Show
from tests.shows.utils import create_random_show
from tests.utils.utils import build_random_model


def create_random_channel(
    db: Session,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> Channel:
    channel = build_random_model(Channel, user_id=user_id, **kwargs)
    db.add(channel)
    # Flush so channel.shows and channel.queue can be accessed.
    db.flush()
    return channel


def create_random_channel_show(
    db: Session,
    channel: Channel | ChannelOutput | None = None,
    show: Show | None = None,
    *,
    plugin: Plugin | None = None,
    user_id: uuid.UUID | None = None,
    **kwargs: object,
) -> ChannelShow:
    if channel is None:
        channel = create_random_channel(db, user_id=user_id)
    if show is None:
        show = create_random_show(db, plugin=plugin, user_id=user_id)
    channel_show = build_random_model(
        ChannelShow,
        channel_id=channel.id,
        show_id=show.id,
        **kwargs,
    )
    db.add(channel_show)
    # Flush so channel_show.show can be accessed.
    db.flush()
    return channel_show


def create_random_channel_queue(
    db: Session,
    channel: Channel,
    **kwargs: object,
) -> ChannelQueue:
    channel_queue = build_random_model(
        ChannelQueue,
        channel_id=channel.id,
        **kwargs,
    )
    db.add(channel_queue)
    db.flush()
    return channel_queue
