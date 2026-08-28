# TODO: Validate


import uuid

from fastapi import APIRouter

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
)
from app.channels import service
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelCanonicalShow,
    ReadableChannel,
)
from app.channels.models import Channel, ChannelQueue
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelCreate,
    ChannelFavoriteUpdate,
    ChannelOptions,
    ChannelOrderInput,
    ChannelOutput,
    ChannelQueueOutput,
    ChannelShowMembership,
    ChannelUpdate,
    CombinedChannelInput,
    WhitelistEpisodeOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.media.service import delete_record
from app.schemas import Message
from app.shows.dependencies import ExistingShow

channels_router = APIRouter(prefix="/channels", tags=["channels"])


# TODO: Validate
@channels_router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the `User`."""
    return service.create_channel(session, current_user, channel_in)


# TODO: Validate
@channels_router.patch("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by EditableChannel
def update_channel(
    session: SessionDep,
    channel: EditableChannel,
    channel_in: ChannelUpdate,
) -> Channel:
    """Update and return a `Channel` if it's editable by the `User`."""
    return channel_in.update(session, channel)


# TODO: Validate
@channels_router.delete("/{channel_id}")  # noqa: FAST003 - Used by EditableChannel
def delete_channel(session: SessionDep, channel: EditableChannel) -> Message:
    """Delete a `Channel` if it's editable by the `User`."""
    return delete_record(session, channel)


# TODO: Validate
@channels_router.post("/bulk-import-queue")
def bulk_import_queue_urls(
    session: SessionDep,
    current_user: CurrentUser,
    entries: dict[uuid.UUID, list[str]],
) -> Message:
    """Add URLs to multiple channels' import queues at once."""
    return service.bulk_import_queue_urls(session, current_user, entries)


# TODO: Validate
@channels_router.get("/favorite-ids")
def get_favorite_channel_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[uuid.UUID]:
    """List the ids of the `Channel`s the current `User` has favorited."""
    return service.favorite_channel_ids(session, current_user)


# TODO: Validate
@channels_router.post("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Favorite a `Channel` if it's readable by the `User`."""
    return service.favorite_channel(session, current_user, channel)


# TODO: Validate
@channels_router.patch("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def update_favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
    favorite_in: ChannelFavoriteUpdate,
) -> Message:
    """Set the `User`'s private name/number for a favorited `Channel`."""
    return service.update_channel_favorite(
        session,
        current_user,
        channel,
        favorite_in,
    )


# TODO: Validate
@channels_router.delete("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def unfavorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Remove a `Channel` from the `User`'s favorites."""
    return service.unfavorite_channel(session, current_user, channel)


# TODO: Validate
@channels_router.put(
    "/{channel_id}/combined-channels",  # noqa: FAST003 - Used by EditableChannel.
)
def update_channel_combined_channels(
    session: SessionDep,
    current_user: CurrentUser,
    channel: EditableChannel,
    combined_channels: list[CombinedChannelInput],
) -> Message:
    """Replace a `Channel`'s `CombinedChannel`s."""
    return service.replace_combined_channels(
        session,
        current_user,
        channel,
        combined_channels,
    )


# FAST003 - Parameter is used by EditableChannelCanonicalShow.
# TODO: Validate
@channels_router.get(
    "/{channel_id}/whitelist/{canonical_show_id}/filtered-episodes",  # noqa: FAST003
)
def get_channel_whitelist_filtered_episodes(
    session: SessionDep,
    channel_show: EditableChannelCanonicalShow,
) -> list[WhitelistEpisodeOutput]:
    """Read the episodes of a title that an entry names, whatever season they are in."""
    return service.filtered_whitelist_episodes(session, channel_show)


# FAST003 - Parameter is used by EditableChannelCanonicalShow.
# TODO: Validate
@channels_router.patch("/{channel_id}/whitelist/{canonical_show_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: EditableChannelCanonicalShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    return service.update_whitelist_output(session, whitelist_config, channel_show)


# FAST003 - Parameter is used by EditableChannel.
# TODO: Validate
@channels_router.post("/{channel_id}/blacklist-episode")  # noqa: FAST003
def blacklist_channel_episode(
    session: SessionDep,
    channel: EditableChannel,
    blacklist_in: BlacklistEpisodeInput,
) -> Message:
    """Blacklist a single episode for a `Channel`."""
    return service.blacklist_episode_by_show_id(session, channel, blacklist_in)


# FAST003 - Parameter is used by EditableChannel.
# TODO: Validate
@channels_router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_default_order(
    session: SessionDep,
    channel: EditableChannel,
    channel_options: ChannelOptions,
) -> Channel:
    """Update the default sort order for a `Channel`."""
    return service.set_default_order(session, channel, channel_options)


# FAST003 - Parameter is used by EditableChannel.
# TODO: Validate
@channels_router.patch("/{channel_id}/order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_order(
    session: SessionDep,
    channel: EditableChannel,
    order_input: ChannelOrderInput,
) -> Channel:
    """Set the custom episode order for a `Channel`."""
    return service.set_custom_order(session, channel, order_input)


# FAST003 - Parameter is used by ExistingShow.
# TODO: Validate
@channels_router.get("/for-show/{show_id}")  # noqa: FAST003
def get_channels_for_show(
    session: SessionDep,
    current_user: CurrentUser,
    show: ExistingShow,
) -> list[ChannelShowMembership]:
    """List the `User`'s `Channel`s, saying which already hold a title."""
    return service.channels_with_show_membership(session, current_user, show)


# FAST003 - Parameters are used by EditableChannel and ExistingShow.
# TODO: Validate
@channels_router.post("/{channel_id}/add-show/{show_id}")  # noqa: FAST003
def add_channel_show(
    session: SessionDep,
    channel: EditableChannel,
    show: ExistingShow,
) -> Message:
    """Put a title, on every website it is on, onto a `Channel`."""
    return service.add_show(session, channel, show)


# FAST003 - Parameters are used by EditableChannelCanonicalShow.
# TODO: Validate
@channels_router.delete("/{channel_id}/remove-show/{canonical_show_id}")  # noqa: FAST003
def delete_channel_show(
    session: SessionDep,
    channel_show: EditableChannelCanonicalShow,
) -> Message:
    """Remove a title, on every website it is on, from a `Channel`."""
    return service.remove_show(session, channel_show)


# TODO: Validate
@channels_router.get(
    "/{channel_id}/import-queue",  # noqa: FAST003 - Used by EditableChannel
    response_model=list[ChannelQueueOutput],
)
def get_channel_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> list[ChannelQueue]:
    """Read the URLs in a channel's import queue."""
    return service.channel_queue(session, channel)


# TODO: Validate
@channels_router.post(
    "/{channel_id}/import-queue",  # noqa: FAST003 - Used by EditableChannel
    response_model=list[ChannelQueueOutput],
)
def create_channel_queue_urls(
    session: SessionDep,
    channel: EditableChannel,
    urls: list[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    return service.add_queue_urls(session, channel, urls)


# TODO: Validate
@channels_router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003 - Used by EditableChannel.
def delete_channel_queue_url(
    session: SessionDep,
    channel: EditableChannel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    return service.delete_queue_url(session, channel, url_id)


# TODO: Validate
@channels_router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003 - Used by EditableChannel.
def clear_channel_completed_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> Message:
    """Clear a channel's import queue."""
    return service.clear_completed_queue(session, channel)


router = APIRouter()


router.include_router(channels_router)
