# TODO: Validate
"""The channels a read covers, and which of them the viewer may see.

A channel can combine other channels, and those can combine further ones, so a
read of one channel is a read of everything reachable from it that the viewer is
allowed to see.
"""

from collections.abc import Collection, Sequence
from uuid import UUID

from sqlmodel import col, or_, select

from app.auth.dependencies import SessionDep
from app.channels.models import Channel
from app.models import Visibility
from app.users.models import User


def child_channel_ids(channel: Channel) -> list[UUID]:
    """Return the additional channel ids combined into a channel, in order."""
    return [combined.combined_channel_id for combined in channel.combined_channels]


def readable_channels(
    session: SessionDep,
    user: User | None,
    channel_ids: Collection[UUID],
) -> Sequence[Channel]:
    """Return the channels the user is allowed to read from the given ids."""
    query = select(Channel).where(col(Channel.id).in_(channel_ids))
    readable = col(Channel.visibility).in_(
        (Visibility.public, Visibility.unlisted),
    )
    if user is None:
        query = query.where(readable)
    elif not user.is_superuser:
        query = query.where(or_(readable, col(Channel.user_id) == user.id))

    return session.exec(query).all()


def resolve_channel_ids(
    session: SessionDep,
    user: User | None,
    main_channel: Channel,
    additional_channels: Collection[UUID],
) -> set[UUID]:
    """Resolve the full set of readable channel ids reachable from a channel.

    Starts from the main channel plus `additional_channels` and follows each
    readable channel's children (its own `additional_channels`) recursively.
    """
    all_channel_ids = {main_channel.id}
    queued_channel_ids = {main_channel.id}
    to_expand = set(additional_channels) - queued_channel_ids

    while to_expand:
        queued_channel_ids.update(to_expand)
        children: set[UUID] = set()
        for channel in readable_channels(session, user, to_expand):
            all_channel_ids.add(channel.id)
            children.update(child_channel_ids(channel))
        to_expand = children - queued_channel_ids

    return all_channel_ids
