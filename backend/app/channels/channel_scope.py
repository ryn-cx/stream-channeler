# TODO: Validate
"""The channels a read covers, and which of them the viewer may see.

A channel can combine other channels, and those can combine further ones, so a
read of one channel is a read of everything reachable from it that the viewer is
allowed to see.
"""

from collections.abc import Collection, Sequence
from uuid import UUID

from sqlmodel import Session, col, or_, select

from app.channels.models import Channel
from app.models import Visibility
from app.users.models import User


# TODO: Validate
def child_channel_ids(channel: Channel) -> list[UUID]:
    """Return the additional channel ids combined into a channel, in order."""
    return [combined.combined_channel_id for combined in channel.combined_channels]


# TODO: Validate
def readable_channels(
    session: Session,
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


# TODO: Validate
def channel_attribution(
    session: Session,
    user: User | None,
    main_channel: Channel,
) -> dict[UUID, UUID]:
    """Map every channel a read covers to the channel it was added through.

    A combined channel can combine further ones, and an episode from a channel
    that deep reads as belonging to whichever channel was added here rather than
    to the one holding it, so a grandchild's episodes are its parent's. A channel
    reachable through two of them belongs to the first that reaches it.
    """
    attribution = {main_channel.id: main_channel.id}
    # The whole level is read at once rather than a walk per child, so the depth of
    # the tree rather than its width is what this costs.
    to_expand = {
        child_id: child_id
        for child_id in child_channel_ids(main_channel)
        if child_id not in attribution
    }

    while to_expand:
        descendants: dict[UUID, UUID] = {}
        for channel in readable_channels(session, user, to_expand):
            added_through = to_expand[channel.id]
            attribution[channel.id] = added_through
            for descendant_id in child_channel_ids(channel):
                if descendant_id not in attribution:
                    descendants.setdefault(descendant_id, added_through)
        to_expand = descendants

    return attribution


# TODO: Validate
def resolve_channel_ids(
    session: Session,
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
