import uuid

from sqlmodel import Session

from app.channels.models import Channel, ChannelQueue, ChannelShow
from app.channels.schemas import ChannelOutput
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.shows.utils import create_random_show
from tests.users.utils import CreatedUser, create_random_user
from tests.utils.utils import build_random_model


def create_random_channel(
    db: Session,
    user: User | CreatedUser | uuid.UUID | None = None,
    **kwargs: object,
) -> Channel:
    if user is None:
        user = create_random_user(db)
    if isinstance(user, (User, CreatedUser)):
        user = user.id
    channel = build_random_model(Channel, user_id=user, **kwargs)
    db.add(channel)
    db.flush()  #   Allows channel.shows and channel.queue to be accessed.
    return channel


def create_random_channel_show(
    db: Session,
    channel: Channel | ChannelOutput,
    parent: User | CreatedUser | Show | Source | Plugin | uuid.UUID | None = None,
    **kwargs: object,
) -> ChannelShow:
    if not isinstance(parent, Show):
        parent = create_random_show(db, parent)
    channel_show = build_random_model(
        ChannelShow,
        channel_id=channel.id,
        show_id=parent.id,
        **kwargs,
    )
    db.add(channel_show)
    db.flush()  # Allows channel.shows and channel.queue to be accessed.
    return channel_show


def create_random_channel_queue(
    db: Session,
    channel: Channel,
    **kwargs: object,
) -> ChannelQueue:
    channel_queue = build_random_model(ChannelQueue, channel_id=channel.id, **kwargs)
    db.add(channel_queue)
    db.flush()  # Allows channel.shows and channel.queue to be accessed.
    return channel_queue
