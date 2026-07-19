# TODO: Validate
import time
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from loguru import logger
from sqlmodel import col, select

from app.auth.dependencies import (
    CurrentUser,
    SessionDep,
    SuperUser,
    get_current_active_superuser,
)
from app.channels import service
from app.channels.dependencies import (
    EditableChannel,
    EditableChannelReadableShow,
    ExistingChannel,
    ReadableChannel,
)
from app.channels.episode_selector import (
    EpisodeQueryBuilder,
    child_channel_ids,
    readable_channels,
    resolve_channel_ids,
)
from app.channels.models import Channel, ChannelFavorite, ChannelQueue, ChannelShow
from app.channels.schemas import (
    BlacklistEpisodeInput,
    ChannelAdminUpdate,
    ChannelCreate,
    ChannelEpisodesOutput,
    ChannelFavoriteUpdate,
    ChannelListOutput,
    ChannelOptions,
    ChannelOrderInput,
    ChannelOutput,
    ChannelQueueAdminOutput,
    ChannelQueueAdminUpdate,
    ChannelQueueOutput,
    ChannelReadOptions,
    ChannelShowGroup,
    ChannelShowsOutput,
    ChannelsPublic,
    ChannelUpdate,
    CombinedChannelOutput,
    EpisodeWithDetails,
    SortOptionOutput,
    WhitelistEpisodeOutput,
    WhitelistSeasonOutput,
    WhitelistShowInput,
    WhitelistShowOutput,
)
from app.media.schemas import MediaOwner
from app.media.service import delete_record
from app.plugins.schemas import PluginOutput
from app.schemas import Message
from app.seasons.schemas import SeasonOutput
from app.shows.models import Show
from app.shows.schemas import ShowPublic
from app.sources.schemas import SourcePublic
from app.users.dependencies import OptionalUser
from app.users.models import User
from app.users.service import get_or_create_plugin_user

channels_router = APIRouter(prefix="/channels", tags=["channels"])
admin_router = APIRouter(
    prefix="/admin/channels",
    tags=["channels"],
    dependencies=[Depends(get_current_active_superuser)],
)


@channels_router.post("", response_model=ChannelOutput)
def create_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel_in: ChannelCreate,
) -> Channel:
    """Create a `Channel` owned by the `User`."""
    channel = Channel.model_validate(channel_in, update={"user_id": current_user.id})
    session.add(channel)
    session.commit()
    return channel


@channels_router.get("")
def get_channels(
    session: SessionDep,
    current_user: OptionalUser,
    read_options: Annotated[ChannelReadOptions, Query()],
) -> ChannelsPublic:
    """Get `Channel`s."""
    return service.scoped_channel_list_output(session, current_user, read_options)


@channels_router.patch("/{channel_id}", response_model=ChannelOutput)  # noqa: FAST003 - Used by EditableChannel
def update_channel(
    session: SessionDep,
    channel: EditableChannel,
    channel_in: ChannelUpdate,
) -> Channel:
    """Update and return a `Channel` if it's editable by the `User`."""
    return channel_in.update(session, channel)


@channels_router.delete("/{channel_id}")  # noqa: FAST003 - Used by EditableChannel
def delete_channel(session: SessionDep, channel: EditableChannel) -> Message:
    """Delete a `Channel` if it's editable by the `User`."""
    return delete_record(session, channel)


@channels_router.get("/sort-options")
def get_sort_options() -> list[SortOptionOutput]:
    """Get a list of all possible sorting options."""
    return service.get_sort_options()


@channels_router.post("/bulk-import-queue")
def bulk_import_queue_urls(
    session: SessionDep,
    current_user: CurrentUser,
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
    for channel_id, urls in entries.items():
        if channel := channels_by_id.get(channel_id):
            service.add_urls_to_channel_import_queue(
                session=session,
                urls=urls,
                channel=channel,
            )
            total_urls += len(urls)
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Channel {channel_id} not found",
            )
    return Message(message=f"{total_urls} URLs added across {len(entries)} channels")


@channels_router.get("/favorite-ids")
def get_favorite_channel_ids(
    session: SessionDep,
    current_user: CurrentUser,
) -> list[uuid.UUID]:
    """List the ids of the `Channel`s the current `User` has favorited.

    Unreadable favorites are left in because this only drives the favorite toggle;
    the `favorites` scope of the list endpoint is what applies the read rules.
    """
    return list(
        session.exec(
            select(ChannelFavorite.channel_id).where(
                ChannelFavorite.user_id == current_user.id,
            ),
        ).all(),
    )


@channels_router.post("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Favorite a `Channel` if it's readable by the `User`."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        session.add(ChannelFavorite(user_id=current_user.id, channel_id=channel.id))
        session.commit()
    return Message(message="Channel favorited successfully")


@channels_router.patch("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def update_favorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
    favorite_in: ChannelFavoriteUpdate,
) -> Message:
    """Set the `User`'s private name/number for a favorited `Channel`.

    Favoriting the channel first if it isn't already, so personalizing it from the
    favorites view can never race against the favorite not yet existing.
    """
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is None:
        favorite = ChannelFavorite(user_id=current_user.id, channel_id=channel.id)
        session.add(favorite)
    favorite.name = favorite_in.name
    favorite.channel_number = favorite_in.channel_number
    session.commit()
    return Message(message="Favorite updated successfully")


@channels_router.delete("/{channel_id}/favorite")  # noqa: FAST003 - Used by ReadableChannel.
def unfavorite_channel(
    session: SessionDep,
    current_user: CurrentUser,
    channel: ReadableChannel,
) -> Message:
    """Remove a `Channel` from the `User`'s favorites."""
    favorite = session.get(ChannelFavorite, (current_user.id, channel.id))
    if favorite is not None:
        session.delete(favorite)
        session.commit()
    return Message(message="Channel unfavorited successfully")


@admin_router.patch(
    "/{channel_id}",  # noqa: FAST003 - Used by ExistingChannel.
)
def admin_update_channel(
    session: SessionDep,
    channel: ExistingChannel,
    channel_in: ChannelAdminUpdate,
) -> ChannelListOutput:
    """Update any field on any `Channel` as an admin, including `score`."""
    channel.sqlmodel_update(channel_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(channel)
    username = session.get_one(User, channel.user_id).username
    return ChannelListOutput.model_validate(channel, update={"username": username})


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


@admin_router.get("/queue")
def get_all_channel_queues(
    session: SessionDep,
    current_user: SuperUser,
    owner: MediaOwner | None = None,
) -> list[ChannelQueueAdminOutput]:
    """List every `Channel`'s import queue entries, scoped by owner."""
    selector = (
        select(ChannelQueue, Channel, User.username)
        .join(Channel, col(Channel.id) == ChannelQueue.channel_id)
        .join(User, col(User.id) == Channel.user_id)
        .order_by(col(ChannelQueue.created_at).desc())
    )
    if not owner:
        selector = selector.where(Channel.user_id == current_user.id)
    else:
        plugin_user = get_or_create_plugin_user(session=session)
        if owner == MediaOwner.official:
            selector = selector.where(Channel.user_id == plugin_user.id)
        else:
            selector = selector.where(
                col(Channel.user_id).not_in([current_user.id, plugin_user.id]),
            )
    rows = session.exec(selector).all()
    return [
        _channel_queue_admin_output(channel, username, queue_entry)
        for queue_entry, channel, username in rows
    ]


@admin_router.patch("/queue/{queue_id}")
def admin_update_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
    queue_in: ChannelQueueAdminUpdate,
) -> ChannelQueueAdminOutput:
    """Update a `Channel`'s queue entry as an admin."""
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    queue_entry.sqlmodel_update(queue_in.model_dump(exclude_unset=True))
    session.commit()
    session.refresh(queue_entry)
    channel = session.get_one(Channel, queue_entry.channel_id)
    username = session.get_one(User, channel.user_id).username
    return _channel_queue_admin_output(channel, username, queue_entry)


@admin_router.delete("/queue/{queue_id}")
def admin_delete_channel_queue(
    session: SessionDep,
    queue_id: uuid.UUID,
) -> Message:
    """Delete a `Channel`'s queue entry as an admin."""
    queue_entry = session.exec(
        select(ChannelQueue).where(ChannelQueue.id == queue_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="Queue entry not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


@channels_router.get(
    "/{channel_id}/combined-channels",  # noqa: FAST003 - Used by ReadableChannel.
)
def get_channel_combined_channels(
    channel: ReadableChannel,
    session: SessionDep,
) -> list[CombinedChannelOutput]:
    """Return a `Channel`'s `CombinedChannel`s."""
    result: list[CombinedChannelOutput] = []
    for combined in channel.combined_channels:
        combined_channel = session.get(Channel, combined.combined_channel_id)
        result.append(
            CombinedChannelOutput(
                id=combined.combined_channel_id,
                name=combined_channel.name if combined_channel else None,
            ),
        )
    return result


@channels_router.put(
    "/{channel_id}/combined-channels",  # noqa: FAST003 - Used by EditableChannel.
)
def update_channel_combined_channels(
    session: SessionDep,
    current_user: CurrentUser,
    channel: EditableChannel,
    combined_channel_ids: list[uuid.UUID],
) -> Message:
    """Delete a `Channel`'s `CombinedChannel`s."""
    readable_ids = {
        readable.id
        for readable in readable_channels(session, current_user, combined_channel_ids)
    }
    ordered_ids = [
        combined_id
        for combined_id in combined_channel_ids
        if combined_id in readable_ids
    ]
    service.set_channel_combined_channels(session, channel, ordered_ids)
    return Message(message="Combined channels updated successfully")


@channels_router.get("/{channel_id}/episodes")  # noqa: FAST003 - Used by ReadableChannel.
def get_channel_episodes(
    channel: ReadableChannel,
    channel_options: Annotated[ChannelOptions, Query()],
    user: OptionalUser,
    session: SessionDep,
) -> ChannelEpisodesOutput:
    """Read the episodes for a channel."""
    output = ChannelEpisodesOutput(
        episodes=[],
        seasons={},
        shows={},
        sources={},
        plugins={},
        channels={},
    )

    start = time.time()

    builder = EpisodeQueryBuilder(session, channel, channel_options, user)
    results = builder.get_episodes()

    unique_channel_ids = {
        channel_id for result in results for channel_id in result.channel_ids
    }
    channels = session.exec(
        select(Channel).where(col(Channel.id).in_(unique_channel_ids)),
    ).all()
    for channel_obj in channels:
        output.channels[channel_obj.id] = service.channel_output(channel_obj, user)

    for result in results:
        episode = result.episode
        season = episode.season
        show = season.show
        source = show.source
        plugin = source.plugin

        extras: dict[str, Any] = {
            "channel_id": result.channel_id,
            "channel_ids": result.channel_ids,
        }
        if result.latest_watch:
            extras["watch_date"] = result.latest_watch.watch_date
            extras["verified"] = result.latest_watch.verified
            extras["episode_watch_id"] = result.latest_watch.id

        output.episodes.append(
            EpisodeWithDetails(**episode.model_dump(), **extras),
        )

        if episode.season_id not in output.seasons:
            output.seasons[episode.season_id] = SeasonOutput.model_validate(season)
        if season.show_id not in output.shows:
            output.shows[season.show_id] = ShowPublic.model_validate(show)
        if show.source_id not in output.sources:
            output.sources[show.source_id] = SourcePublic.model_validate(source)
        if source.plugin_id not in output.plugins:
            output.plugins[source.plugin_id] = PluginOutput.model_validate(plugin)

    logger.info("get_channel_episodes completed in {:.3f} seconds", time.time() - start)
    return output


# FAST003 - Parameter is used by ReadableChannel.
@channels_router.get("/{channel_id}/shows")  # noqa: FAST003
def get_channel_shows(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> ChannelShowsOutput:
    """Read all shows for a channel, including those from its child channels."""
    output = ChannelShowsOutput()

    channel_ids = resolve_channel_ids(
        session,
        user,
        channel,
        child_channel_ids(channel),
    )
    channel_shows = session.exec(
        select(ChannelShow).where(col(ChannelShow.channel_id).in_(channel_ids)),
    ).all()

    # A show can appear in several of the combined channels; deduplicate by show id.
    # A show counts as a regular show if any channel includes it normally, even when
    # another channel only uses it for filtering.
    regular_shows: dict[uuid.UUID, ShowPublic] = {}
    filter_only_shows: dict[uuid.UUID, ShowPublic] = {}
    # Regular shows kept per channel so they can be grouped by where they come from.
    shows_by_channel: dict[uuid.UUID, dict[uuid.UUID, ShowPublic]] = {}
    channel_names: dict[uuid.UUID, str | None] = {}
    for channel_show in channel_shows:
        show = channel_show.show
        source = show.source
        plugin = source.plugin

        if not plugin.is_readable(session, user):
            continue

        if channel_show.is_blacklist_only:
            filter_only_shows.setdefault(show.id, ShowPublic.model_validate(show))
        else:
            regular_shows.setdefault(show.id, ShowPublic.model_validate(show))
            channel_group = shows_by_channel.setdefault(channel_show.channel_id, {})
            channel_group.setdefault(show.id, ShowPublic.model_validate(show))
            channel_names.setdefault(channel_show.channel_id, channel_show.channel.name)

        if source.id not in output.sources:
            output.sources[source.id] = SourcePublic.model_validate(source)

    output.shows = list(regular_shows.values())
    output.filter_only_shows = [
        show
        for show_id, show in filter_only_shows.items()
        if show_id not in regular_shows
    ]

    # The channel the request was made on comes first; the rest follow by name.
    def group_sort_key(group_channel_id: uuid.UUID) -> tuple[bool, str]:
        is_not_primary = group_channel_id != channel.id
        return (is_not_primary, (channel_names.get(group_channel_id) or "").lower())

    output.groups = [
        ChannelShowGroup(
            channel_id=group_channel_id,
            channel_name=channel_names.get(group_channel_id),
            shows=sorted(
                shows_by_channel[group_channel_id].values(),
                key=lambda show: (show.name or "").lower(),
            ),
        )
        for group_channel_id in sorted(shows_by_channel, key=group_sort_key)
    ]

    return output


# FAST003 - Parameter is used by ReadableChannel.
@channels_router.get("/{channel_id}/sources")  # noqa: FAST003
def get_channel_sources(
    channel: ReadableChannel,
    user: OptionalUser,
    session: SessionDep,
) -> list[SourcePublic]:
    """Read all unique sources for a channel."""
    sources: dict[uuid.UUID, SourcePublic] = {}
    for channel_show in channel.shows:
        source = channel_show.show.source
        plugin = source.plugin

        if not plugin.is_readable(session, user):
            continue

        if source.id not in sources:
            sources[source.id] = SourcePublic.model_validate(source)

    return list(sources.values())


# FAST003 - Parameter is used by UserChannelShow.
@channels_router.get("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def get_channel_whitelist(
    channel_show: EditableChannelReadableShow,
) -> WhitelistShowOutput:
    """Read the whitelist for a show in a channel."""
    enabled_season_ids = {x.season_id for x in channel_show.season_filters}
    enabled_episode_ids = {x.episode_id for x in channel_show.episode_filters}
    episode_expiries = {
        episode_filter.episode_id: episode_filter.expires_at
        for episode_filter in channel_show.episode_filters
    }

    seasons: list[WhitelistSeasonOutput] = []
    episodes: list[WhitelistEpisodeOutput] = []

    for season in channel_show.show.seasons:
        seasons.append(
            WhitelistSeasonOutput.model_validate(
                season,
                update={"filtered": season.id in enabled_season_ids},
            ),
        )
        episodes.extend(
            WhitelistEpisodeOutput.model_validate(
                episode,
                update={
                    "filtered": episode.id in enabled_episode_ids,
                    "expires_at": episode_expiries.get(episode.id),
                },
            )
            for episode in season.episodes
        )

    return WhitelistShowOutput.model_validate(
        channel_show.show,
        update={
            "is_whitelist": channel_show.is_whitelist,
            "seasons": seasons,
            "episodes": episodes,
        },
    )


# FAST003 - Parameter is used by UserChannelShow.
@channels_router.patch("/{channel_id}/whitelist/{show_id}")  # noqa: FAST003
def update_channel_whitelist(
    session: SessionDep,
    whitelist_config: WhitelistShowInput,
    channel_show: EditableChannelReadableShow,
) -> WhitelistShowOutput:
    """Update the whitelist/blacklist for a show in a channel."""
    service.update_whitelist(session, channel_show, whitelist_config)
    # Build the response before any cleanup so it stays valid even if the
    # channel-show is removed below.
    output = get_channel_whitelist(channel_show)
    # A filter-only show that no longer hides anything serves no purpose, so drop it
    # to keep the channel's show list clean.
    if (
        channel_show.is_blacklist_only
        and not channel_show.season_filters
        and not channel_show.episode_filters
    ):
        session.delete(channel_show)
        session.commit()
    return output


# FAST003 - Parameter is used by EditableChannel.
@channels_router.post("/{channel_id}/blacklist-episode")  # noqa: FAST003
def blacklist_channel_episode(
    session: SessionDep,
    channel: EditableChannel,
    blacklist_in: BlacklistEpisodeInput,
) -> Message:
    """Blacklist a single episode for a `Channel`.

    When the show is not already on the channel a filter-only `ChannelShow` is
    created so the episode can be hidden without making the whole show a member of the
    channel. An optional `expires_at` makes the blacklist temporary.
    """
    # Show's primary key is (source_id, key), so look it up by its id column.
    show = session.exec(
        select(Show).where(Show.id == blacklist_in.show_id),
    ).first()
    if show is None:
        raise HTTPException(status_code=404, detail="Show not found")

    service.blacklist_episode_on_channel(
        session=session,
        channel=channel,
        show=show,
        episode_id=blacklist_in.episode_id,
        expires_at=blacklist_in.expires_at,
    )
    return Message(message="Episode blacklisted successfully")


# FAST003 - Parameter is used by UserChannel.
@channels_router.patch("/{channel_id}/default-order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_default_order(
    session: SessionDep,
    channel: EditableChannel,
    channel_options: ChannelOptions,
) -> Channel:
    """Update the default sort order for a `Channel`."""
    exclude: set[str] = set()
    if "random_seed" not in channel_options.model_fields_set:
        exclude.add("random_seed")
    channel.default_order = channel_options.model_dump_json(
        by_alias=True,
        exclude_defaults=True,
        exclude_unset=False,
        exclude=exclude,
    )
    session.commit()
    session.refresh(channel)
    return channel


# FAST003 - Parameter is used by EditableChannel.
@channels_router.patch("/{channel_id}/order", response_model=ChannelOutput)  # noqa: FAST003
def update_channel_order(
    session: SessionDep,
    channel: EditableChannel,
    order_input: ChannelOrderInput,
) -> Channel:
    """Set the custom episode order for a `Channel`."""
    service.set_channel_order(session, channel, order_input.episode_ids)
    session.refresh(channel)
    return channel


# FAST003 - Parameters are used by EditableChannelReadableShow.
@channels_router.delete("/{channel_id}/remove-show/{show_id}")  # noqa: FAST003
def delete_channel_show(
    session: SessionDep,
    channel_show: EditableChannelReadableShow,
) -> Message:
    """Remove a `Show` from a `Channel`."""
    session.delete(channel_show)
    session.commit()
    return Message(
        message=f"{channel_show.show.name} removed from channel successfully",
    )


@channels_router.get(
    "/{channel_id}/import-queue",  # noqa: FAST003 - Used by UserChannel
    response_model=list[ChannelQueueOutput],
)
def get_channel_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> list[ChannelQueue]:
    """Read the URLs in a channel's import queue."""
    statement = (
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        # Descending order works better on the frontend because new URLs are appended to the
        # top of the list making it possible to immediately see the new URLs after adding
        # them without having to scroll down.
        .order_by(col(ChannelQueue.created_at).desc())
    )

    channels = session.exec(statement).all()

    return list(channels)


@channels_router.post(
    "/{channel_id}/import-queue",  # noqa: FAST003 - Used by UserChannel
    response_model=list[ChannelQueueOutput],
)
def create_channel_queue_urls(
    session: SessionDep,
    channel: EditableChannel,
    urls: list[str],
) -> list[ChannelQueue]:
    """Add URLs to a channel's import queue."""
    return service.add_urls_to_channel_import_queue(
        session=session,
        urls=urls,
        channel=channel,
    )


@channels_router.delete("/{channel_id}/import-queue/{url_id}")  # noqa: FAST003 - Used by UserChannel.
def delete_channel_queue_url(
    session: SessionDep,
    channel: EditableChannel,
    url_id: uuid.UUID,
) -> Message:
    """Delete url from a channel's import queue."""
    queue_entry = session.exec(
        select(ChannelQueue)
        .where(ChannelQueue.channel_id == channel.id)
        .where(ChannelQueue.id == url_id),
    ).first()
    if not queue_entry:
        raise HTTPException(status_code=404, detail="URL not found")
    url = queue_entry.url
    session.delete(queue_entry)
    session.commit()
    return Message(message=f"{url} removed from import queue successfully")


@channels_router.delete("/{channel_id}/clear-completed-import-queue")  # noqa: FAST003 - Used by UserChannel.
def clear_channel_completed_queue(
    session: SessionDep,
    channel: EditableChannel,
) -> Message:
    """Clear a channel's import queue."""
    for queue_entry in channel.queue:
        if queue_entry.status == service.URLStatus.IMPORTED:
            session.delete(queue_entry)

    session.commit()
    return Message(message="Import queue cleared successfully")


@channels_router.get("/{channel_id}")  # noqa: FAST003 - Used by ReadableChannel
def get_channel(channel: ReadableChannel, user: OptionalUser) -> ChannelOutput:
    """Get a `Channel` if it's readable by the `User`."""
    return service.channel_output(channel, user)


router = APIRouter()
router.include_router(channels_router)
router.include_router(admin_router)
