# TODO: Validate
import uuid

from sqlmodel import Session

from app.channels.models import Channel, ChannelQueue, ChannelShow
from app.channels.schemas import ChannelOutput
from app.channels.service import shows_for_channel_show
from app.models import Visibility
from app.plugins.models import Plugin
from app.shows.models import Show
from app.sources.models import Source
from app.users.models import User
from tests.app.helpers.utils import build_random_model
from tests.app.shows.utils import create_random_show
from tests.app.users.utils import CreatedUser, create_random_user


# TODO: Validate
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
    kwargs.setdefault("anonymous", False)
    # TODO: If tests pass this can be deleted.
    # kwargs.setdefault("score", 0)
    channel = build_random_model(Channel, user_id=user, **kwargs)
    session.add(channel)
    session.flush()  #   Allows channel.shows and channel.queue to be accessed.
    return channel


# TODO: Validate
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
        canonical_show_id=parent.sole_canonical_show_id or parent.id,
        **kwargs,
    )
    session.add(channel_show)
    session.flush()  # Allows channel.shows and channel.queue to be accessed.
    return channel_show


# TODO: Validate
def channel_show_show(session: Session, channel_show: ChannelShow) -> Show:
    """Return the `Show` the `ChannelShow` stands for.

    A `ChannelShow` names a title rather than one website's copy of it, and a test
    only ever creates the one copy, so the first match is that copy.
    """
    return shows_for_channel_show(session, channel_show)[0]


# TODO: Validate
def create_random_channel_queue(
    session: Session,
    channel: Channel,
    **kwargs: object,
) -> ChannelQueue:
    channel_queue = build_random_model(ChannelQueue, channel_id=channel.id, **kwargs)
    session.add(channel_queue)
    session.flush()  # Allows channel.shows and channel.queue to be accessed.
    return channel_queue
