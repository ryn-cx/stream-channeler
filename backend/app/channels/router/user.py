# TODO: Validate


import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
)
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelQueueEntry,
    EditableChannelTmdbTitle,
    ReadableChannel,
)
from app.channels.models import Channel
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelBuildPlugin,
    ChannelCreate,
    ChannelFavoriteUpdate,
    ChannelOptions,
    ChannelOrderInput,
    ChannelOutput,
    ChannelQueuePage,
    ChannelTitleMembership,
    ChannelUpdate,
    CombinedChannelInput,
    WhitelistEpisodeOutput,
    WhitelistTitleInput,
    WhitelistTitleOutput,
)
from app.channels.service import (
    builder,
    channels,
    combined,
    favorites,
    import_queue,
    ordering,
    titles,
    whitelist,
)
from app.channels.service.import_queue import CHANNEL_QUEUE_PAGE
from app.media.service.deletion import delete_record
from app.schemas import Message
from app.titles.dependencies import ExistingTitle

channels_router = APIRouter(prefix="/channels", tags=["channels"])


# TODO: Validate
@channels_router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the `User`."""
    return channels.create_channel(session, current_user, channel_in)


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
    return import_queue.bulk_import_queue_urls(session, current_user, entries)


# TODO: Validate
@channels_router.get("/favorite-ids")
def get_favorite_channel_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[uuid.UUID]:
    """List the ids of the `Channel`s the current `User` has favorited."""
    return favorites.favorite_channel_ids(session, current_user)


# TODO: Validate
@channels_router.post("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Favorite a `Channel` if it's readable by the `User`."""
    return favorites.favorite_channel(session, current_user, channel)


# TODO: Validate
@channels_router.patch("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def update_favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
    favorite_in: ChannelFavoriteUpdate,
) -> Message:
    """Set the `User`'s private name/number for a favorited `Channel`."""
    return favorites.update_channel_favorite(
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
    return favorites.unfavorite_channel(session, current_user, channel)


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
    return combined.replace_combined_channels(
        session,
        current_user,
        channel,
        combined_channels,
    )


# TODO: Validate
@channels_router.get(
    "/{channel_id}/whitelist/{tmdb_title_id}/filtered-episodes",  # noqa: FAST003
)
def get_channel_whitelist_filtered_episodes(
    session: SessionDep,
    channel_title: EditableChannelTmdbTitle,
) -> list[WhitelistEpisodeOutput]:
    """Read the episodes of a title that an entry names, whatever season they are in."""
    return whitelist.filtered_whitelist_episodes(session, channel_title)


# TODO: Validate
@channels_router.patch("/{channel_id}/whitelist/{tmdb_title_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistTitleInput,
    channel_title: EditableChannelTmdbTitle,
) -> WhitelistTitleOutput:
    """Update the whitelist/blacklist for a title in a channel."""
    return whitelist.update_whitelist_output(session, whitelist_config, channel_title)


# TODO: Validate
@channels_router.post("/{channel_id}/blacklist-episode")  # noqa: FAST003
def blacklist_channel_episode(
    session: SessionDep,
    channel: EditableChannel,
    blacklist_in: BlacklistEpisodeInput,
) -> Message:
    """Blacklist a single episode for a `Channel`."""
    return whitelist.blacklist_episode_by_title_id(session, channel, blacklist_in)


# TODO: Validate
@channels_router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_default_order(
    session: SessionDep,
    channel: EditableChannel,
    channel_options: ChannelOptions,
) -> Channel:
    """Update the default sort order for a `Channel`."""
    return ordering.set_default_order(session, channel, channel_options)


# TODO: Validate
@channels_router.patch("/{channel_id}/order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_order(
    session: SessionDep,
    channel: EditableChannel,
    order_input: ChannelOrderInput,
) -> Channel:
    """Set the custom episode order for a `Channel`."""
    return ordering.set_custom_order(session, channel, order_input)


# TODO: Validate
@channels_router.get("/for-title/{title_id}")  # noqa: FAST003
def get_channels_for_title(
    session: SessionDep,
    current_user: CurrentUser,
    title: ExistingTitle,
) -> list[ChannelTitleMembership]:
    return titles.channels_with_title_membership(session, current_user, title)


# TODO: Validate
@channels_router.post("/{channel_id}/add-title/{title_id}")  # noqa: FAST003
def add_channel_title(
    session: SessionDep,
    channel: EditableChannel,
    title: ExistingTitle,
) -> Message:
    """Put a title, on every website it is on, onto a `Channel`."""
    return titles.add_title(session, channel, title)


# TODO: Validate
@channels_router.get("/{channel_id}/build-from-title/{title_id}/plugins")  # noqa: FAST003
def get_channel_build_plugins(
    session: SessionDep,
    channel: EditableChannel,  # noqa: ARG001 - Checks the user may edit the channel.
    title: ExistingTitle,
) -> list[ChannelBuildPlugin]:
    return builder.buildable_plugins(session, title)


# TODO: Validate
@channels_router.post("/{channel_id}/build-from-title/{title_id}")  # noqa: FAST003
def build_channel_from_title(
    session: SessionDep,
    channel: EditableChannel,
    title: ExistingTitle,
    plugin_keys: list[str] | None = None,
) -> Message:
    return builder.build_from_title(session, channel, title, plugin_keys)


# TODO: Validate
@channels_router.delete("/{channel_id}/remove-title/{tmdb_title_id}")  # noqa: FAST003
def delete_channel_title(
    session: SessionDep,
    channel_title: EditableChannelTmdbTitle,
) -> Message:
    """Remove a title, on every website it is on, from a `Channel`."""
    return titles.remove_title(session, channel_title)


# TODO: Validate
@channels_router.get("/{channel_id}/import-queue")  # noqa: FAST003
def get_channel_queue(
    session: SessionDep,
    channel: EditableChannel,
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=CHANNEL_QUEUE_PAGE)] = CHANNEL_QUEUE_PAGE,
    query: Annotated[str | None, Query()] = None,
) -> ChannelQueuePage:
    """Read the URLs in a channel's import queue."""
    return import_queue.channel_queue(session, channel, offset, limit, query)


# TODO: Validate
@channels_router.post("/{channel_id}/import-queue")  # noqa: FAST003
def create_channel_queue_urls(
    session: SessionDep,
    channel: EditableChannel,
    urls: list[str],
) -> Message:
    """Add URLs to a channel's import queue."""
    import_queue.add_urls_to_channel_import_queue(session, channel, urls)
    return Message(message=f"{len(urls)} URLs added to the import queue")


# TODO: Validate
@channels_router.post("/{channel_id}/import-queue/{url_id}/retry")  # noqa: FAST003
def retry_channel_queue_url(
    session: SessionDep,
    queue_entry: EditableChannelQueueEntry,
) -> Message:
    """Put one URL back into a channel's import queue to be imported again."""
    return import_queue.retry_queue_entry(session, queue_entry)


# TODO: Validate
@channels_router.post("/{channel_id}/import-queue/retry-failed")  # noqa: FAST003
def retry_failed_channel_queue_urls(
    session: SessionDep,
    _admin: SuperUser,
    channel: EditableChannel,
) -> Message:
    """Put every URL a channel's queue gave up on back into it.

    Admin-only, unlike the retry beside it: one press starts as many imports as
    the queue has failures, which is a load on every website they are read from
    rather than a load here.
    """
    return import_queue.retry_failed_queue_entries(session, channel)


# TODO: Validate
@channels_router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003
def delete_channel_queue_url(
    session: SessionDep,
    queue_entry: EditableChannelQueueEntry,
) -> Message:
    """Delete url from a channel's import queue."""
    return import_queue.delete_queue_entry(session, queue_entry)


# TODO: Validate
@channels_router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003
def clear_channel_completed_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> Message:
    """Clear a channel's import queue."""
    return import_queue.clear_completed_queue(session, channel)


router = APIRouter()


router.include_router(channels_router)
