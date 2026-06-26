# TODO: Validate
import uuid

from sqlmodel import Session

from app.channels.models import Channel, ChannelQueue, ChannelShow
from app.channels.schemas import ChannelOutput
from app.models import Visibility
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import CreatedUser, create_random_user
from tests.app.utils.utils import build_random_model


def create_random_channel(
    session: Session,
    user: User | CreatedUser | uuid.UUID | None = None,
    *,
    is_public: bool | None = None,
    **kwargs: object,
) -> Channel:
    if user is None:
        user = create_random_user(session)
    if isinstance(user, (User, CreatedUser)):
        user = user.id
    if is_public is not None and "visibility" not in kwargs:
        kwargs["visibility"] = Visibility.public if is_public else Visibility.private
    kwargs.setdefault("default_order", None)
    channel = build_random_model(Channel, user_id=user, **kwargs)
    session.add(channel)
    session.flush()  #   Allows channel.shows and channel.queue to be accessed.
    return channel


def create_random_channel_show(
    session: Session,
    channel: Channel | ChannelOutput,
    parent: User | CreatedUser | Show | Source | Plugin | uuid.UUID | None = None,
    **kwargs: object,
) -> ChannelShow:
    if not isinstance(parent, Show):
        parent = create_random_show(session, parent)
    kwargs.setdefault("is_blacklist_only", False)
    channel_show = build_random_model(
        ChannelShow,
        channel_id=channel.id,
        show_id=parent.id,
        **kwargs,
    )
    session.add(channel_show)
    session.flush()  # Allows channel.shows and channel.queue to be accessed.
    return channel_show


def create_random_channel_queue(
    session: Session,
    channel: Channel,
    **kwargs: object,
) -> ChannelQueue:
    channel_queue = build_random_model(ChannelQueue, channel_id=channel.id, **kwargs)
    session.add(channel_queue)
    session.flush()  # Allows channel.shows and channel.queue to be accessed.
    return channel_queue
