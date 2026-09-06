# TODO: Validate
import uuid

from sqlmodel import Session

from app.channels.models import Channel, ChannelQueue, ChannelTitle
from app.channels.schemas import ChannelOutput
from app.channels.service.titles import titles_for_channel_title
from app.models import Visibility
from app.plugins.models import Plugin
from app.sources.models import Source
from app.titles.models import Title
from app.users.models import User
from tests.app.helpers.utils import build_random_model
from tests.app.titles.utils import create_random_title
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
    session.flush()  #   Allows channel.titles and channel.queue to be accessed.
    return channel


# TODO: Validate
def create_random_channel_title(
    session: Session,
    channel: Channel | ChannelOutput,
    parent: User | CreatedUser | Title | Source | Plugin | uuid.UUID | None = None,
    **kwargs: object,
) -> ChannelTitle:
    if not isinstance(parent, Title):
        parent = create_random_title(session, parent)
    kwargs.setdefault("is_blacklist_only", False)
    channel_title = build_random_model(
        ChannelTitle,
        channel_id=channel.id,
        canonical_title_id=parent.sole_canonical_title_id or parent.id,
        **kwargs,
    )
    session.add(channel_title)
    session.flush()  # Allows channel.titles and channel.queue to be accessed.
    return channel_title


# TODO: Validate
def channel_title_title(session: Session, channel_title: ChannelTitle) -> Title:
    """Return the `Title` the `ChannelTitle` stands for.

    A `ChannelTitle` names a title rather than one website's copy of it, and a test
    only ever creates the one copy, so the first match is that copy.
    """
    return titles_for_channel_title(session, channel_title)[0]


# TODO: Validate
def create_random_channel_queue(
    session: Session,
    channel: Channel,
    **kwargs: object,
) -> ChannelQueue:
    channel_queue = build_random_model(ChannelQueue, channel_id=channel.id, **kwargs)
    session.add(channel_queue)
    session.flush()  # Allows channel.titles and channel.queue to be accessed.
    return channel_queue
